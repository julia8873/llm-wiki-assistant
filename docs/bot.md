# Plugin Bot Maubot (`llm-wiki-assistant-plugin`)

## Estado de Implementación
El código fuente del bot ha sido implementado progresivamente en las Fases 5, 5.1 y 6. 
Estructura base disponible en `moodle-matrix-dev/maubot/llm-wiki-assistant-plugin/`.

## Arquitectura de Clientes LLM
El sistema abstrae la capa de inferencia usando implementaciones concretas que siguen una interfaz común `LLMClient`. El proveedor activo se selecciona desde `config/config.yaml` en la clave `llm.proveedor_activo`.

1. **`OpenAICompatibleClient`**: Cliente genérico que utiliza el estándar de la industria (`/v1/chat/completions`). Es parametrizable vía `api_base_url` y `api_key_env_var`. Se utiliza para:
   - **OpenAI** (Si configuras `llm.proveedor_activo: "openai"`).
   - **Ollama** (Inferencia local).
2. **`GeminiClient`**: Cliente dedicado para Google Gemini debido a que utiliza una estructura de API REST diferente (Activo por defecto con `llm.proveedor_activo: "gemini"`).

Para cambiar de proveedor, simplemente edita `config/config.yaml`, establece `proveedor_activo` al deseado y reinicia los contenedores. Las credenciales se inyectan automáticamente como variables de entorno (las keys reales están referenciadas en el yaml o mediante `.env`).

## Aislamiento Estricto y Proveedor Git
1. **Trigger**: Recepción de mensaje de texto en sala Matrix (se ignoran los propios).
2. **Aislamiento de Seguridad (Solo Lectura del Repo Propio)**: Llama a `mapeo-api` (`GET /mapeos?matrix_room_id={room_id}`) para obtener de forma segura la URL del repositorio del alumno y su `git_provider`. **El bot NUNCA toca el repositorio oficial del profesor ni puede acceder a repositorios de otros estudiantes.** No tiene conocimiento global.
3. **Selección de Credenciales Dinámica**: Dependiendo del valor de `git_provider` retornado por la API, el módulo `git_utils.py` inyecta automáticamente el token de acceso correspondiente (ej. `GITHUB_PAT` o `GITLAB_TOKEN`) directamente en la URL para el clonado seguro por HTTPS.
4. **Indexación Vectorial**: El bot trocea los ficheros OKF y los indexa.
5. **Respuesta**: Se genera contexto RAG y se contesta, citando fuentes.

## Estructura de Carpetas en el Repositorio del Alumno (Prevención de Colisiones)
Para permitir que múltiples procesos interactúen sobre el mismo repositorio Git del estudiante sin colisionar (Bot RAG, Sync Ascendente, Logging de Interacciones), la estructura de carpetas tiene dueños estrictamente segregados.

| Carpeta / Fichero | Qué es y para qué sirve | Quién / Qué proceso escribe en ella |
|-------------------|--------------------------|--------------------------------------|
| `material-oficial/` | Contenido oficial (teoría/práctica) inyectado por el profesor desde la asignatura. | **Sincronización Ascendente** (Fase 5.1). Los workers lo sobrescriben al haber push en el repo oficial. |
| `conceptos/`, `entidades/`, `recursos/` | Ficheros OKF generados tras la ingesta de documentos subidos por el alumno al chat. | **Bot (Ingesta OKF)**. Añade conocimiento extraído de archivos del usuario. |
| `bitacora/log.md` | Registro de las acciones de ingesta o comandos de reversión (`!deshacer`). | **Bot (Ingesta OKF)**. |
| `logs/interacciones/` | Ficheros JSON estructurados con cada Q&A (chat) del usuario con el bot. | **Worker de Logs** (Fase 6). Tarea asíncrona encolada por el bot. |
| `logs/log.txt` | Histórico general plano (append) de acciones de sync o ingesta. | **Worker de Sync** y **Bot (Ingesta OKF)**. |
| `raw/` | Archivos PDF/Imágenes originales subidos. | **Bot (Ingesta OKF)**. |

Gracias a este esquema, un sincronismo del profesor nunca borra el chat del estudiante, y una respuesta de chat nunca rompe el material oficial. Todo ocurre bajo un **cerrojo distribuido (Distributed Lock de Redis)** para evitar carreras en Git.

## Ingesta de Archivos (OKF v0.1)
El bot es capaz de ingerir documentos arrastrados al chat:
1. Detecta la subida y pregunta el método de extracción (Normal o Multimodal/OCR).
2. Extrae el texto y aplica la plantilla `AGENTS.md` (ahora leída desde `material-oficial/AGENTS.md` localmente) como system prompt.
3. Inyecta Frontmatter YAML, añade a Git (`git add .`), realiza commit y hace un push automatizado al repositorio.

## Comandos Interactivos
- **`!ayuda` / `!comandos`**: Menú dinámico de asistencia.
- **`!deshacer` / `!revertir`**: Revierte el último commit (`git revert`) en Git si fue una ingesta automática, limpiando la memoria vectorial.
- **`!sincronizar` / `!sync`**: Fuerza a demanda la actualización del repositorio del estudiante trayendo los cambios desde el material oficial del profesor.

## Configuración e Instanciación del Bot (Maubot Manager)
(Esta configuración ya se hace automáticamente con `./instalar.sh bot package` y configurando el cliente desde la UI de Maubot).
- **Homeserver:** `http://synapse:8008`
- **User ID:** `@llm_wiki_bot:localhost`
