# API y Almacén de Mapeo

El núcleo del sistema llm-wiki-assistant confía en una arquitectura desacoplada para vincular un Alumno con su respectiva asignatura, su repositorio GitHub (Fork) y su sala de Matrix. 

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
- **`POST /mapeos`**: Crea un nuevo mapeo.
- **`POST /cursos`**: Provisión del repositorio oficial de un curso.
- **`POST /sync/oficial-updated`**: Webhook de sincronización asíncrona para actualizar los forks de los alumnos con los cambios del material del profesor (Fase 5.1).
- **`GET /mapeos?moodle_user_id={id}&moodle_course_id={id}`**: Busca el mapeo de un estudiante en un curso (devuelve `404` si no existe).
- **`GET /mapeos/by-room/{matrix_room_id}`**: Busca el repositorio asignado a una sala específica de Matrix (usado por el Bot).
