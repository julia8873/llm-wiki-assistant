# API y Almacén de Mapeo

El núcleo del sistema llm-wiki-assistant confía en una arquitectura desacoplada para vincular un Alumno con su respectiva asignatura, su repositorio Git (generado desde un template oficial) y su sala de Matrix. 

## Decisiones de Diseño (Fase 2)
Se eligió la **Opción B (Microservicio FastAPI)** en lugar de una tabla nativa de Moodle por las siguientes razones:
- **Desacoplamiento Estricto**: Moodle (`block_bdc`) y el Bot (`maubot`) acceden a un almacén central agnóstico por HTTP. Ninguno necesita credenciales de base de datos del otro.
- **Seguridad**: El microservicio no publica su puerto al exterior ni al *host*; solo es accesible dentro de la red interna de contenedores `docker-compose.yml`. Además, se protege con un token de acceso compartido (`MAPEO_API_TOKEN`). El contenedor `mapeo-api` valida este token durante el arranque; si detecta que está vacío o que contiene valores por defecto (`changeme`, `default_token`), la aplicación abortará inmediatamente con un error fatal en los logs para evitar exponer una API desprotegida en producción.
- **Integración con GitHub**: El PAT de GitHub se lee desde la variable de entorno `GITHUB_PAT`, que se genera automáticamente desde `config/config.yaml` y no necesita declararse manualmente en los `.env.example`.

## Almacenamiento y Backup
El servicio utiliza **SQLite** y la base de datos reside en el volumen nombrado `mapeo_api_data` definido en Docker Compose, el cual se monta en `/data` dentro del contenedor.
- **Archivo**: `/data/mapeos.db`
- **Estrategia de Backup**: Debido a que SQLite no bloquea lecturas concurrentes, pero sí escrituras, es recomendable hacer un *dump* o copiar el archivo del volumen directamente (`docker run --rm -v moodle-matrix-dev_mapeo_api_data:/data alpine tar czf /data/backup.tar.gz /data/mapeos.db`) de forma programada y síncrona junto con los backups de Moodle.

## Esquema de Base de Datos
| Columna | Tipo | Restricción |
|---|---|---|
| `id` | Integer | Primary Key |
| `moodle_user_id` | Integer | Not Null |
| `moodle_course_id` | Integer | Not Null |
| `repo_url` | String | Nullable |
| `official_repo_url` | String | Nullable |
| `git_provider` | String | Not Null (Defecto: github) |
| `matrix_room_id` | String | Nullable |
| `estado` | String | Defecto: PENDIENTE_GITHUB |
| `is_teacher` | Integer | Defecto: 0 |
| `moodle_username` | String | Nullable |
| `created_at` | DateTime | Auto UTC |
| `updated_at` | DateTime | Auto UTC onUpdate |

*Nota: Existe una restricción única compuesta (`moodle_user_id`, `moodle_course_id`) para garantizar que un alumno solo tenga un repositorio asociado por curso.*

## Referencia OpenAPI (Swagger)
Al estar desarrollado en FastAPI, la documentación interactiva OpenAPI y los esquemas JSON de los endpoints se auto-generan y pueden consultarse internamente accediendo a `http://mapeo-api:8000/docs` desde cualquier contenedor conectado a la red.

### Endpoints Principales

Todos los endpoints requieren el header: `Authorization: Bearer <MAPEO_API_TOKEN>`.

- **`GET /health`**: Healthcheck (200 OK). No requiere token.

- **`POST /mapeos`**: Crea un nuevo mapeo aprovisionando un repositorio y una sala.
  ```bash
  curl -X POST "http://mapeo-api:8000/mapeos" \
       -H "Authorization: Bearer <MAPEO_API_TOKEN>" \
       -H "Content-Type: application/json" \
       -d '{"moodle_user_id": 4, "moodle_course_id": 2, "moodle_username": "student"}'
  ```

- **`GET /mapeos?matrix_room_id={id}`**: Busca el mapeo asociado a una sala específica de Matrix (usado extensivamente por el Bot para localizar el repositorio).
  ```bash
  curl -X GET "http://mapeo-api:8000/mapeos?matrix_room_id=!xyz:localhost" \
       -H "Authorization: Bearer <MAPEO_API_TOKEN>"
  ```

- **`POST /sync/oficial-updated`**: Webhook de sincronización asíncrona. Recibe un payload de GitHub/GitLab tras un push en el repositorio oficial y encola tareas en Redis para actualizar los repositorios de los alumnos. Validado por HMAC (`X-Hub-Signature-256`).
  ```bash
  # Ejemplo simplificado de cómo GitHub llama a este endpoint
  curl -X POST "http://mapeo-api:8000/sync/oficial-updated" \
       -H "X-Hub-Signature-256: sha256=..." \
       -H "Content-Type: application/json" \
       -d '{"repository": {"clone_url": "https://github.com/org/repo-Oficial.git"}}'
  ```
