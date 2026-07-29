# Gestión de Credenciales y Seguridad

## Regla de Oro
**Prohibido versionar secretos.** El repositorio jamás almacena tokens, passwords o claves privadas.

## Inyección de Secretos
El entorno se inicializa copiando ficheros `.example` a su versión real. La versión real es ignorada por Git.

| Fichero Plantilla (Versionado) | Fichero Final (Ignorado) | Alcance |
|---|---|---|
| `.env.example` | `.env` | Variables globales Docker (`OPENAI_API_KEY`, PAT de GitHub, DB Password). |
| `config/config.yaml.example` | `config/config.yaml` | Configuración estructural y de puertos. |
| `base-config.yaml.example` | `moodle-matrix-dev/maubot/base-config.yaml` | Servidor base Maubot. |
| `config.yaml.example` | `moodle-matrix-dev/maubot/config.yaml` | Plugin específico Maubot. |
