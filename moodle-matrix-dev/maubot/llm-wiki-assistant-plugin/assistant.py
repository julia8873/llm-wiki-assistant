import os
import logging
from typing import Dict, Any
from ruamel.yaml import YAML

yaml = YAML(typ='safe')

from maubot import Plugin, MessageEvent
from maubot.handlers import event
from mautrix.types import EventType, TextMessageEventContent
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

    async def stop(self) -> None:
        if hasattr(self, 'vector_store'):
            await self.vector_store.close()

    @event.on(EventType.ROOM_ENCRYPTED)
    async def handle_encrypted(self, evt: MessageEvent) -> None:
        self.log.error(f"RECIBIDO EVENTO ENCRIPTADO SIN DESENCRIPTAR: sender={evt.sender}, room={evt.room_id}")

    @event.on(EventType.ROOM_MESSAGE)
    async def handle_message(self, evt: MessageEvent) -> None:
        self.log.info(f"RECIBIDO EVENTO: sender={evt.sender}, type={type(evt.content)}, content={evt.content}")
        # Ignorar mensajes del propio bot
        if evt.sender == self.client.mxid:
            return
            
        # Solo procesar mensajes de texto
        if not isinstance(evt.content, TextMessageEventContent):
            self.log.info(f"Ignorado: No es TextMessageEventContent (es {type(evt.content)})")
            return
            
        if evt.content.msgtype != "m.text" and str(evt.content.msgtype) != "m.text":
            self.log.info(f"Ignorado: msgtype no es m.text (es {evt.content.msgtype})")
            return
            
        query = evt.content.body
        room_id = evt.room_id
        
        self.log.info(f"Mensaje procesado: '{query}' de {evt.sender} en {room_id}")
        
        try:
            # 1. Resolver el repositorio
            repo_url, git_provider = await self.mapeo_client.get_room_mapping(room_id)
            
            # 2. Clonar/Actualizar e indexar
            await evt.mark_read()
            # Opcional: enviar un "escribiendo..." mientras clona/indexa
            await self.client.set_typing(room_id, timeout=10000)
            
            await self.repo_reader.process_repository(repo_url, git_provider)
            
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
