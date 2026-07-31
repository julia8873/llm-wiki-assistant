import os
import logging
from typing import Dict, Any
from ruamel.yaml import YAML

yaml = YAML(typ='safe')

from maubot import Plugin, MessageEvent
from maubot.handlers import event
from mautrix.types import EventType, TextMessageEventContent, MediaMessageEventContent
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper

from mixins.mapeo_client import MapeoClient, MapeoClientError
from mixins.repo_reader import RepoReader, RepoReaderError
from mixins.vector_store import VectorStore
from mixins.llm_clients import get_llm_client, LLMClientError

class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        pass # Nosotros leemos config.yaml centralizado, no usamos la config nativa de maubot

class LLMWikiAssistantPlugin(Plugin):
    async def start(self) -> None:
        # Cargar config.yaml centralizado
        config_path = "/config/config.yaml"
        if not os.path.exists(config_path):
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config.yaml")
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                self.app_config = yaml.load(f)
        except Exception as e:
            self.log.error(f"Error cargando config.yaml: {e}")
            self.app_config = {}

        self.system_prompt = self.app_config.get("llm", {}).get("system_prompt", "Eres un asistente.")
        
        mapeo_api_token = os.environ.get("MAPEO_API_TOKEN", "")
        mapeo_api_url = os.environ.get("MAPEO_API_URL", "http://mapeo-api:8000")
        
        self.mapeo_client = MapeoClient(mapeo_api_url, mapeo_api_token)
        
        # Postgres DSN para pgvector
        pg_user = os.environ.get("PGVECTOR_USER", "llm_wiki")
        pg_pass = os.environ.get("PGVECTOR_PASSWORD", "llm_wiki_pass")
        pg_db = os.environ.get("PGVECTOR_DB", "vector_store")
        pg_host = os.environ.get("PGVECTOR_HOST", "pgvector")
        
        dsn = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:5432/{pg_db}"
        self.vector_store = VectorStore(dsn)
        
        try:
            await self.vector_store.connect()
        except Exception as e:
            self.log.error(f"No se pudo conectar a pgvector: {e}")

        try:
            self.llm_client = get_llm_client(self.app_config)
            self.repo_reader = RepoReader(self.app_config, self.vector_store, self.llm_client)
        except Exception as e:
            self.log.error(f"Error inicializando clientes LLM/Repo: {e}")

        self.pending_files = {}

    async def stop(self) -> None:
        if hasattr(self, 'vector_store'):
            await self.vector_store.close()

    @event.on(EventType.ROOM_ENCRYPTED)
    async def handle_encrypted(self, evt: MessageEvent) -> None:
        self.log.error(f"RECIBIDO EVENTO ENCRIPTADO SIN DESENCRIPTAR: sender={evt.sender}, room={evt.room_id}")

    @event.on(EventType.ROOM_MESSAGE)
    async def handle_message(self, evt: MessageEvent) -> None:
        """!
        @brief Procesa los mensajes entrantes de los usuarios en la sala de Matrix.
        
        Gestiona:
        - Recepcion de ficheros para ingesta automatica OKF.
        - Comandos directos (!ayuda, !deshacer).
        - Consultas de chat (QA) utilizando RAG sobre el repositorio del alumno.
        
        @param evt Evento del mensaje de Matrix.
        """
        self.log.info(f"RECIBIDO EVENTO: sender={evt.sender}, type={type(evt.content)}")
        if evt.sender == self.client.mxid:
            return

        # 1. Manejo de archivos (media)
        if isinstance(evt.content, MediaMessageEventContent):
            if str(evt.content.msgtype) in ["m.file", "m.document", "m.image"]:
                self.pending_files[evt.sender] = {
                    "url": evt.content.url,
                    "filename": evt.content.body
                }
                await evt.respond(
                    f"He recibido el archivo '{evt.content.body}'. ¿Quieres que haga una ingesta automática del documento para extraer sus conceptos?\n\n"
                    "Responde con una de estas opciones:\n"
                    "- **si**: Ingesta normal (rápida, ideal para texto claro).\n"
                    "- **ocr**: Procesarlo usando Inteligencia Artificial visual (ideal para imágenes o apuntes a mano).\n"
                    "- **no**: Cancelar la operación."
                )
            return

        # 2. Solo procesar mensajes de texto
        if not isinstance(evt.content, TextMessageEventContent):
            return
            
        if evt.content.msgtype != "m.text" and str(evt.content.msgtype) != "m.text":
            return
            
        query = evt.content.body.strip()
        lower_q = query.lower()
        room_id = evt.room_id
        
        # 3. Comprobar si el usuario estaba en estado de confirmacion de archivo
        if evt.sender in self.pending_files:
            if lower_q in ["si", "sí", "ocr"]:
                use_ocr = (lower_q == "ocr")
                file_info = self.pending_files.pop(evt.sender)
                await evt.respond("Procesando documento... (esto puede tardar un poco mientras la IA extrae los conceptos y se guardan en GitHub).")
                try:
                    repo_url, official_repo_url, git_provider = await self.mapeo_client.get_room_mapping(room_id)
                    data = await self.client.download_media(file_info["url"])
                    
                    await self.repo_reader.ingest_file_okf(
                        repo_url=repo_url,
                        official_repo_url=official_repo_url,
                        git_provider=git_provider,
                        filename=file_info["filename"],
                        file_bytes=data,
                        use_ocr=use_ocr
                    )
                    
                    # Re-indexar el repo ahora que tiene los nuevos conceptos .md
                    await self.repo_reader.process_repository(repo_url, official_repo_url, git_provider)
                    
                    await evt.respond(f"¡Listo! El archivo ha sido analizado y sus conceptos han sido extraídos mediante {'OCR Multimodal' if use_ocr else 'Extracción Normal'} y guardados correctamente en tu repositorio. Ya puedes preguntarme sobre ellos.")
                except Exception as e:
                    self.log.error(f"Error procesando archivo {file_info['filename']}: {e}")
                    await evt.respond(f"Ha ocurrido un error al procesar el archivo. Detalles: {e}")
            elif lower_q in ["no", "cancelar"]:
                self.pending_files.pop(evt.sender)
                await evt.respond("Operación cancelada. El archivo ha sido ignorado.")
            else:
                await evt.respond("Por favor, responde 'si', 'ocr' o 'no'.")
            return
            
        # 4. Procesamiento de Comandos Directos
        if lower_q in ["!ayuda", "!comandos"]:
            await evt.respond(
                "### 🛠️ Comandos Disponibles\n\n"
                "- **`!ayuda`** / **`!comandos`**: Muestra este menú de ayuda.\n"
                "- **`!deshacer`** / **`!revertir`**: Revierte la última ingesta automática de un documento (elimina sus conceptos y olvida la información).\n"
                "- **`!sincronizar`**: Sincroniza tu repositorio con los últimos materiales oficiales de la asignatura.\n\n"
                "💡 *Puedes subir archivos al chat y te preguntaré si quieres analizarlos usando IA normal o IA Visual (OCR).* \n"
                "💡 *Cualquier otro texto que escribas lo tomaré como una pregunta sobre tu base de conocimiento.*"
            )
            return
            
        if lower_q in ["!deshacer", "!revertir"]:
            await evt.respond("Comprobando el historial... intentando revertir la última ingesta de documento.")
            try:
                repo_url, official_repo_url, git_provider = await self.mapeo_client.get_room_mapping(room_id)
                success = await self.repo_reader.revert_last_ingest(repo_url, official_repo_url, git_provider)
                if success:
                    # Re-indexar para borrar de la BD vectorial los documentos borrados
                    await self.repo_reader.process_repository(repo_url, official_repo_url, git_provider)
                    await evt.respond("✅ ¡Hecho! La última ingesta de documento ha sido revertida en el repositorio. La IA ha olvidado sus conceptos y se ha borrado todo rastro de ella.")
                else:
                    await evt.respond("❌ No se ha podido revertir. Parece que la última acción en el repositorio no fue una ingesta automática, o ya fue revertida.")
            except Exception as e:
                self.log.error(f"Error al revertir: {e}")
                await evt.respond(f"❌ Ocurrió un error al intentar deshacer: {e}")
            return
            
        if lower_q in ["!sincronizar", "!sync"]:
            await evt.respond("Iniciando sincronización manual con los materiales del profesor...")
            try:
                repo_url, official_repo_url, git_provider = await self.mapeo_client.get_room_mapping(room_id)
                # Ejecutamos la tarea de sync directamente (bloqueando) para el comando manual
                from sync_worker.tasks import _async_sync_repo_task
                await _async_sync_repo_task(room_id, repo_url, official_repo_url)
                
                # Re-indexar el repo
                await self.repo_reader.process_repository(repo_url, official_repo_url, git_provider)
                await evt.respond("✅ Sincronización completada. Ya tienes los últimos materiales del profesor.")
            except Exception as e:
                self.log.error(f"Error al sincronizar manualmente: {e}")
                await evt.respond(f"❌ Ocurrió un error durante la sincronización: {e}")
            return
            
        self.log.info(f"Mensaje procesado: '{query}' de {evt.sender} en {room_id}")
        
        try:
            # 1. Resolver el repositorio
            repo_url, official_repo_url, git_provider = await self.mapeo_client.get_room_mapping(room_id)
            
            # 2. Clonar/Actualizar e indexar
            await evt.mark_read()
            # Opcional: enviar un "escribiendo..." mientras clona/indexa
            await self.client.set_typing(room_id, timeout=10000)
            
            await self.repo_reader.process_repository(repo_url, official_repo_url, git_provider)
            
            # 3. Buscar contexto
            results = await self.repo_reader.search(repo_url, query, limit=5)
            
            # 4. Generar respuesta
            system_prompt_with_context = f"{self.system_prompt}\n\n"
            
            try:
                repo_files = await self.vector_store.get_all_files(repo_url)
                if repo_files:
                    system_prompt_with_context += "Lista de todos los ficheros disponibles en este repositorio:\n- " + "\n- ".join(repo_files) + "\n\n"
            except Exception as e:
                self.log.warning(f"Error obteniendo lista de ficheros: {e}")

            system_prompt_with_context += "Contexto recuperado:\n"
            if not results:
                system_prompt_with_context += "(No se encontró contexto detallado en el repositorio para esta consulta concreta)\n"
            else:
                for i, chunk in enumerate(results):
                    system_prompt_with_context += f"--- Chunk {i+1} (Fichero: {chunk['file_path']}) ---\n{chunk['content']}\n\n"
            
            user_prompt = f"Pregunta: {query}"
            
            response_text = await self.llm_client.get_response(system_prompt_with_context, user_prompt)
            
            await evt.respond(response_text)
            
        except MapeoClientError as e:
            self.log.error(f"Error de mapeo: {e}")
            await evt.respond(f"Esta sala no tiene un repositorio vinculado. Detalles: {str(e)}")
        except RepoReaderError as e:
            self.log.error(f"Error accediendo al repositorio: {e}")
            await evt.respond(f"Ha ocurrido un error accediendo al repositorio vinculado. Detalles: {str(e)}")
        except LLMClientError as e:
            self.log.error(f"Error del LLM: {e}")
            await evt.respond(f"Ha ocurrido un error conectando con el motor de IA. Detalles: {str(e)}")
        except Exception as e:
            self.log.error(f"Error inesperado procesando mensaje: {e}", exc_info=True)
            await evt.respond(f"Ha ocurrido un error interno. Detalles: {str(e)}")
