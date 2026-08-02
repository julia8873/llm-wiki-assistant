# Gestión de Credenciales y Seguridad

## Regla de Oro
**Prohibido versionar secretos.** El repositorio jamás almacena tokens, passwords o claves privadas.

## Patrón de Secretos `.example` / `.gitignore`
El entorno se inicializa copiando ficheros `.example` a su versión real. La versión real (`.env`, `config.yaml`, etc.) está rígidamente ignorada por Git (`.gitignore`).

| Fichero Plantilla (Versionado) | Fichero Final (Ignorado) | Alcance |
|---|---|---|
| `.env.example` | `.env` | Variables globales Docker y secretos de API. |
| `config/config.yaml.example` | `config/config.yaml` | Configuración estructural, puertos y claves maestras. |
| `base-config.yaml.example` | `moodle-matrix-dev/maubot/base-config.yaml` | Servidor base Maubot. |
| `config.yaml.example` | `moodle-matrix-dev/maubot/config.yaml` | Plugin específico Maubot. |

## Credenciales de API (LLM)
Las variables utilizadas dependen del proveedor configurado en `llm.proveedor_activo` en `config.yaml`:
- **`OPENAI_API_KEY`**: Usada si se selecciona `openai`.
- **`GEMINI_API_KEY`**: Usada si se selecciona `gemini`.

## Tokens de Proveedores Git (Mutuamente Excluyentes)
El sistema inyecta el token en las URLs HTTPS de clonado dinámicamente según el proveedor configurado (`git.proveedor_activo`). **No se cargan todos a la vez**, sólo el activo.
- **`GITHUB_PAT`**: Token de Acceso Personal para GitHub.
- **`GITLAB_TOKEN`**: Token de Acceso Personal para GitLab.
- **`GIT_SELF_HOSTED_TOKEN`**: Token reservado/no usado en producción actualmente. Su proveedor asociado (`self_hosted_provider.py`) es un STUB por diseño.

## Bases de Datos (PostgreSQL y MariaDB)
- **`MARIADB_USER` / `MARIADB_PASSWORD`**: Credenciales para la base de datos MariaDB utilizada por el LMS Moodle.
- **`POSTGRES_USER` / `POSTGRES_PASSWORD`**: Credenciales introducidas en la Fase 9.1 para securizar el acceso de Mapeo API a PostgreSQL en producción. Evitan el uso de usuarios root.
- **`DATABASE_URL`**: Cadena de conexión parametrizada que incluye las credenciales. Utilizada por el ORM SQLAlchemy en Mapeo API de forma transparente.

## Seguridad Entre Subsistemas (Comunicaciones Internas)
- **`MAPEO_API_TOKEN`**: (Fase 2). Generado automáticamente por `./instalar.sh` con `openssl rand -hex 32` en el `.env` (si estaba en modo `changeme`). Protege las llamadas internas del Moodle (`block_bdc`) y Maubot hacia la API. *Ningún subsistema (Maubot, Sync-Worker, etc.) se conecta directamente a la base de datos de mapeo; todas las lecturas y escrituras atraviesan esta API HTTP y están securizadas por este token.*
- **`GITHUB_WEBHOOK_SECRET`**: (Fase 5.1). Secreto configurado globalmente usado para validar la firma HMAC (`X-Hub-Signature-256`) de los payloads provenientes del repositorio oficial en el endpoint `POST /sync/oficial-updated`. Sin esta firma, la API rechaza el intento de encolar trabajos.

## Seguridad de Volúmenes y Backups
- **Restricción de Acceso (Fase 9.2)**: El contenedor de `backup` monta el volumen de datos de Redis (`redis_data`) en modo de **solo lectura** (`ro`). Esto previene cualquier riesgo de corrupción accidental del estado de las colas de trabajos desde el script de copias de seguridad.
- **Aislamiento de Postgres**: El script de backup no tiene acceso directo a los ficheros del volumen de PostgreSQL. Extrae la información legítimamente a través del cliente `pg_dump` vía red interna, autenticándose con `POSTGRES_USER` y `POSTGRES_PASSWORD`.
