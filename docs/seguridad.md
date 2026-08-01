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

## Seguridad Entre Subsistemas (Comunicaciones Internas)
- **`MAPEO_API_TOKEN`**: (Fase 2). Generado automáticamente por `./instalar.sh` con `openssl rand -hex 32` en el `.env` (si estaba en modo `changeme`). Protege las llamadas internas del Moodle (`block_bdc`) y Maubot hacia la API.
- **`GITHUB_WEBHOOK_SECRET`**: (Fase 5.1). Secreto configurado globalmente usado para validar la firma HMAC (`X-Hub-Signature-256`) de los payloads provenientes del repositorio oficial en el endpoint `POST /sync/oficial-updated`. Sin esta firma, la API rechaza el intento de encolar trabajos.
