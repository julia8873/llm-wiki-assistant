# Plugin Bot Maubot (`llm-wiki-assistant-plugin`)

## Estado de Implementación
El código fuente del bot ha sido implementado en la **Fase 5**. 
Estructura base disponible en `moodle-matrix-dev/maubot/llm-wiki-assistant-plugin/`.

## Arquitectura de Clientes LLM
El sistema abstrae la capa de inferencia usando dos implementaciones concretas que implementan una interfaz común `LLMClient`:

1. **`OpenAICompatibleClient`**: Cliente genérico que utiliza el estándar de facto de la industria (`/v1/chat/completions`). Es parametrizable vía `api_base_url` y `api_key_env_var`. Se utiliza para:
   - **OpenAI** (Defecto)
   - **Ollama** (Usado con una API Key "dummy", ya que la API de Ollama es compatible de forma nativa).
2. **`GeminiClient`**: Cliente dedicado para Google Gemini debido a que utiliza una estructura de API REST diferente.

**Nota sobre Ollama:**
Ollama es una vía soportada (perfil opcional en Docker) pensada para entornos aislados, offline o pruebas locales. No es el camino primario para entornos de producción debido al alto costo computacional de los embeddings y la inferencia a escala (CPU).

## Ciclo de Ejecución de Chat (QA)
1. **Trigger**: Recepción de mensaje de texto en sala Matrix (se ignoran los propios).
2. **Aislamiento e Identificación**: Llama a `mapeo-api` (`GET /mapeos/by-room/{room_id}`) para obtener de forma segura la URL del repositorio del alumno y su `git_provider`. *El bot NUNCA toca el repositorio oficial de la asignatura*.
3. **Clonado Seguro**: Inyecta el token correcto en la URL (según el `git_provider`) y clona o hace `git pull` localmente de ese repositorio exclusivo.
4. **Indexación Vectorial (pgvector)**: El bot trocea (chunking) los ficheros OKF y los indexa en un motor PostgreSQL. Garantiza el aislamiento forzando la cláusula `WHERE repo_id = ...` en toda búsqueda.
5. **Inferencia y Anti-Injection**: Recupera el contexto usando búsqueda semántica (RAG). El System Prompt restringe al modelo a *no inventar* y a citar siempre el fichero, tratando explícitamente cualquier instrucción del estudiante como dato y no como orden.
6. **Respuesta**: Envío de la respuesta documentada a la sala Matrix.

## Ingesta de Archivos (OKF v0.1)
El bot es capaz de ingerir documentos (ej. PDFs o Imágenes) arrastrados al chat:
1. Detecta la subida y pregunta el método de extracción (Normal o Multimodal/OCR).
2. Extrae el texto utilizando librerías nativas o visión artificial del LLM.
3. Utiliza la plantilla de la asignatura (`AGENTS.md`) como _system prompt_ para clasificar el conocimiento en:
   - `conceptos/`
   - `entidades/`
   - `recursos/`
4. Aplica _XML-based extraction_ (etiquetas `<file path="...">`) para evitar los clásicos fallos de escape de strings JSON de los LLM.
5. Inyecta Frontmatter YAML, añade a Git (`git add .`), realiza commit y hace un push automatizado al repositorio del estudiante.

## Comandos Interactivos
- **`!ayuda` / `!comandos`**: Menú dinámico de asistencia.
- **`!deshacer` / `!revertir`**: Revierte el último commit (`git revert`) en GitHub si fue una ingesta automática, borrando los conceptos generados, documentándolo en la bitácora (`log.md`) y limpiando la memoria del bot.

## Configuración e Instanciación del Bot (Maubot Manager)

Una vez que la infraestructura está levantada y el plugin empaquetado, debes configurar la cuenta del bot y lanzar la instancia desde el gestor web de Maubot.

### 1. Crear el usuario Matrix del Bot
El bot necesita una cuenta real en el servidor de Matrix local (Synapse). Si aún no existe, puedes crearla desde el orquestador o directamente ejecutando en tu terminal:
```bash
docker exec -it moodle-matrix-dev-synapse-1 register_new_matrix_user http://localhost:8008 -c /data/homeserver.yaml -u llm_wiki_bot -p botpass123 -a
```

### 2. Obtener el Access Token
Puedes iniciar sesión con la API para obtener el Token de Acceso que usará Maubot, o extraerlo de Element si inicias sesión allí. Para obtenerlo por consola en Windows/PowerShell:
```powershell
curl.exe -s -X POST http://localhost:8008/_matrix/client/r0/login -d "{\`"type\`":\`"m.login.password\`", \`"user\`":\`"llm_wiki_bot\`", \`"password\`":\`"botpass123\`"}"
```

### 3. Añadir el Cliente a Maubot
1. Inicia sesión en el panel de control de Maubot: **`http://127.0.0.1:29317/_matrix/maubot`** (Usuario: `admin`, Contraseña: `adminpass123`).
2. Ve a la pestaña **Clients** y pulsa **"New client"**.
3. Rellena los datos de la siguiente manera:
   - **User ID:** `@llm_wiki_bot:localhost`
   - **Homeserver:** `http://synapse:8008` *(Importante: usar `synapse` ya que la conexión ocurre internamente en la red Docker).*
   - **Access token:** *(El token extraído en el paso anterior)*
   - **Device ID:** *(El Device ID devuelto junto con el token)*
   - Mantén los demás valores por defecto y pulsa **Create** o **Save**.

### 4. Crear la Instancia del Bot
1. Ve a la pestaña **Instances** y pulsa **"New instance"**.
2. Rellena los datos así:
   - **ID:** `llm-wiki-assistant`
   - **User:** `@llm_wiki_bot:localhost` (El cliente creado en el paso anterior).
   - **Plugin:** `com.llm_wiki.assistant` (Cargado automáticamente gracias al empaquetado de `instalar.sh`).
3. Pulsa **Create** (o Save).

El bot ya está corriendo de fondo escuchando los eventos de Matrix. Puedes abrir **Element** (`http://localhost:8081`), iniciar sesión y probar la funcionalidad iniciando un chat con `@llm_wiki_bot:localhost`.
