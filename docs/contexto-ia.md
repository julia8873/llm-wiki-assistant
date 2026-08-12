# Contexto para Asistentes IA (Project Overview) {#contexto_ia}

Este documento está diseñado específicamente para proporcionar un contexto técnico rápido, denso y estructurado a los asistentes LLM (Inteligencia Artificial) que asistan al usuario en el proyecto para programar, depurar o rediseñar características. Sirve como un atajo cognitivo para que la IA entienda el objetivo y la arquitectura inmediatamente.

## 1. Naturaleza del Proyecto
**Nombre**: LLM Wiki Assistant
**Objetivo**: Crear un ecosistema integrado entre Moodle (LMS), Matrix (Chat federado) y plataformas Git (GitHub/GitLab) que proporcione a los estudiantes un asistente virtual LLM (RAG). El bot interactúa basándose exclusivamente en los apuntes del alumno y material del profesor, promoviendo la base de conocimiento en formato estandarizado **OKF (Open Knowledge Format)**.

## 2. Stack Tecnológico de Infraestructura (Docker Compose)
El proyecto orquesta todos sus servicios mediante `docker-compose.yml` (ubicado en `moodle-matrix-dev/`):
- **LMS**: Moodle (Bitnami) + MariaDB. Puerto expuesto 8000.
- **Chat**: Matrix Synapse + Element Web. Puertos expuestos 8008, 8081. La autenticación en Matrix está delegada (SSO) contra la base de datos de Moodle para un inicio de sesión transparente.
- **Microservicio (API)**: `mapeo-api` construido en FastAPI + PostgreSQL (Alembic para migraciones). Es el servicio fuente de la verdad para la relación relacional: `(ID Alumno, ID Curso) -> (URL Fork Repositorio, ID Sala Matrix)`.
- **Bot LLM**: Maubot (Python). Escucha de forma asíncrona los eventos de las salas. Extrae documentos arrastrados por el usuario al chat, clona repositorios, actualiza memoria vectorial (RAG) y responde al alumno.
- **Workers Asíncronos**: Redis + RQ (Redis Queue). Gestionan tareas pesadas o frágiles en segundo plano sin bloquear el chat:
  - `sync-worker`: Realiza las sincronizaciones del repositorio maestro (del profesor) inyectando o sobreescribiendo la carpeta `material-oficial/` en todos los repositorios de alumnos correspondientes.
  - `log-jobs`: Generación asíncrona de archivos JSONL (guardados en `logs/interacciones/`) con el histórico de preguntas y respuestas RAG para auditoría de uso, evitando saturar la interacción UI del bot.
- **Base de Datos Vectorial**: Usualmente configurada a través de soporte interno u opcional (ej. `pgvector`).

## 3. Patrones de Diseño Críticos y Protecciones
- **Bloque de Moodle (`block_bdc`)**: Plugin PHP que intercepta las acciones en el frontal. Al hacer clic, hace llamadas síncronas a la API interna (`mapeo-api`) y a Synapse para auto-aprovisionar la cuenta Matrix, la sala, el repositorio Git y posteriormente redirigir. Utiliza la *Locking API* de Moodle para evitar problemas de concurrencia ("doble clic") y la creación de salas duplicadas.
- **Distributed Repo Lock (Mutex)**: Para evitar conflictos en el sistema de archivos Git y evitar la corrupción de índices, se usa un cerrojo distribuido nativo en `redis.asyncio`. Ningún worker de sincronización y ningún hilo de Maubot actúan sobre un mismo clon local de Git al mismo tiempo. Tienen TTL de 60s y un thread de heartbeat secundario.
- **Sincronización Git Aislada**: En lugar de hacer un `git pull` genérico que podría ocasionar un merge conflict irresoluble con los cambios del alumno, el sistema realiza la sincronización ascendente ejecutando `git archive upstream/main | tar -x` excluyendo las carpetas personales (`logs/`, `bitacora/`). Esto actualiza `material-oficial/` de manera quirúrgica y previene cualquier sobrescritura destructiva.
- **Fallo Elegante y Reintentos (Exponential Backoff)**: Las peticiones a APIs externas (OpenAI / Gemini) implementan reintentos automáticos y captura de `RetryInfo` frente a códigos de error 429 (Rate Limit) de la capa gratuita (Free Tier).

## 4. Mapa del Código
- `config/config.yaml`: Fuente maestra para toda configuración (LLMs, Git, Moodle, Secretos). El orquestador `instalar.sh` lee este archivo y genera el `.env` dinámicamente.
- `docs/`: Documentación Doxygen estricta (`WARN_AS_ERROR=YES`).
- `moodle-matrix-dev/maubot/llm-wiki-assistant-plugin/`: Contiene el bot Python principal.
  - `mixins/llm_clients.py`: Abstracción multimodelo unificada. Soporta OpenAI-compatibles y de forma nativa a Gemini para análisis multimodal (OCR sobre imágenes/PDFs escaneados).
  - `mixins/repo_reader.py`: Pipeline completo OKF v0.1.
  - `git_utils.py`: Herramientas transaccionales que gestionan clonado por credenciales HTTPS dinámicas en repos y encapsulan el manejo de Locks.
- `moodle-matrix-dev/mapeo-api/`: Backend estructurado modernamente con Pydantic V2 y SQLAlchemy V2.

## 5. Reglas y Convenciones de Modificación (Important)
Si eres una IA a la que se le pide añadir una característica en este sistema, sigue estas premisas:
- **Prioriza la resiliencia**: Cualquier llamada a API o git debe gestionarse de forma defensiva frente a Timeouts.
- **Respeta Doxygen**: Modifica `docs/` asegurándote de no romper los hipervínculos cruzados `\subpage` ni etiquetas de referencias `{#etiqueta}`.
- **Mantén la separación**: No incluyas lógica de enrutamiento web en el código del bot; para ello tienes la API de Mapeo. No satures Moodle; delega en los webhooks externos de la API.
- **Usa variables de entorno seguras**: No incorpores claves (API keys) hardcodeadas en scripts de pruebas. Moodle-Matrix delega sus tokens a través del `.env` autogenerado.
