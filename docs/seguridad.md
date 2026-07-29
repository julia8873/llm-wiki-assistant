# Seguridad y Gestión de Credenciales

En este proyecto, ningún secreto, clave privada o token se sube al repositorio Git.

## Patrón de Secretos

Cada fichero que contenga claves dispone de su correspondiente versión plantilla `.example`:

| Fichero Real (Ignorado) | Fichero Plantilla (Versionado) | Propósito |
| :--- | :--- | :--- |
| `.env` | `.env.example` | Credenciales globales Docker (`OPENAI_API_KEY`, `GEMINI_API_KEY`, DB pass, PAT GitHub) |
| `config/config.yaml` | `config/config.yaml.example` | Configuración centralizada |
| `moodle-matrix-dev/maubot/base-config.yaml` | `moodle-matrix-dev/maubot/base-config.yaml.example` | Servidor Maubot |
| `moodle-matrix-dev/maubot/config.yaml` | `moodle-matrix-dev/maubot/config.yaml.example` | Plugin Maubot |

Todos los ficheros reales están excluidos explícitamente en `.gitignore`.
