# LLM Wiki Assistant

[![Fase Actual](https://img.shields.io/badge/Estado-Fase_7_Completada-success.svg)](docs/index.md)
[![Doxygen](https://img.shields.io/badge/Docs-Doxygen-blue.svg)](Doxyfile)
[![LLM Multi-Provider](https://img.shields.io/badge/LLM-OpenAI_|_Gemini_|_Ollama-blue.svg)](config/config.yaml)
[![Entrypoint](https://img.shields.io/badge/Entrypoint-instalar.sh-orange.svg)](instalar.sh)

Sistema integrado de docencia Moodle-Matrix-Git. Proporciona a cada estudiante una interfaz de chat inteligente en Matrix, atendida por un agente LLM acotado estrictamente a la Base de Conocimiento individual de dicho alumno (generada desde un template oficial del profesor).

*Toda la documentación técnica completa se genera vía Doxygen. Ejecuta `./instalar.sh docs serve` para acceder a ella en [http://localhost:8005](http://localhost:8005).*

## Tabla de Contenidos
- [Configuración Inicial Requerida](#config_inicial)
  - [1. Variables de Entorno (`moodle-matrix-dev/.env`)](#vars_entorno)
  - [2. Configuración Global (`config/config.yaml`)](#config_global)
- [Comandos Operativos Base (Desarrollo)](#comandos_base)
- [Funcionalidades del Bot en Matrix (OKF v0.1)](#funcionalidades_bot)
- [Credenciales de Prueba](#credenciales_prueba)
- [Inventario de Componentes y Carpetas Clave](#inventario_componentes)
- [Fases de Implementación y Estado](#fases_implementacion)

## Configuración Inicial Requerida {#config_inicial}

Antes de levantar el proyecto, debes configurar las credenciales y parámetros de los servicios externos. Estas configuraciones se dividen en dos archivos principales:

### 1. Variables de Entorno (`moodle-matrix-dev/.env`) {#vars_entorno}
Copia el archivo `moodle-matrix-dev/.env.example` a `moodle-matrix-dev/.env` y completa los siguientes valores esenciales:

- **Claves de LLM (Configura solo la del proveedor que vayas a usar):**
  - `OPENAI_API_KEY`: Requerida si usas OpenAI. Consíguela en el panel de [OpenAI API Keys](https://platform.openai.com/api-keys).
  - `GEMINI_API_KEY`: Requerida si usas Google Gemini. Consíguela en [Google AI Studio](https://aistudio.google.com/app/apikey).
  - *(Nota: Si usas Ollama de forma local, no necesitas API Key, pero debes activarlo en `config.yaml`)*.

- **Credenciales de Matrix:**
  - `MATRIX_ACCESS_TOKEN`: Token de administrador necesario para crear salas y usuarios automáticamente.
    - *Cómo obtenerlo:* Una vez levantado Synapse/Element (Fase 1), inicia sesión en tu cliente Element con la cuenta de administrador. Ve a **Ajustes -> Ayuda e información -> Avanzado -> Token de acceso** y cópialo aquí.

- **Tokens Internos Seguros:**
  - `MAPEO_API_TOKEN`: Si lo dejas como `changeme`, el script de instalación (`instalar.sh`) inyectará automáticamente un token seguro generado criptográficamente al vuelo.

### 2. Configuración Global (`config/config.yaml`) {#config_global}
Copia el archivo `config/config.yaml.example` a `config/config.yaml` y revisa los siguientes bloques obligatorios:

- **Configuración del Repositorio (Git):**
  - `git.proveedor_activo`: Elige entre `github`, `gitlab` o `self_hosted`.
  - `git.organizacion`: Tu nombre de usuario o nombre de la organización donde se crearán los repositorios.
  - `git.github.pat`: Tu Personal Access Token (PAT) de GitHub (si usas GitHub).
    - *Cómo obtenerlo:* Ve a [GitHub Developer Settings](https://github.com/settings/tokens). Genera un token (Classic) y asegúrate de marcar al menos el scope completo de `repo`.

- **Selección del Motor LLM:**
  - `llm.proveedor_activo`: Indica el motor de IA que usarás por defecto (`openai`, `gemini`, `ollama`).

## Comandos Operativos Base (Desarrollo) {#comandos_base}

Único punto de entrada: `instalar.sh`.

```bash
# Instalación base y levantamiento de servidor de documentación Doxygen
./instalar.sh

# Levantar infraestructura Docker Compose (Fase 1)
./instalar.sh up [--ollama]

# Levantar servidor de documentación (puerto 8005)
./instalar.sh docs serve

# Verificación estricta de documentación (Falla ante warnings)
./instalar.sh docs check

# Ejecutar Batería de Tests Consolidada (Fase 7)
# Ideal para verificar la instalación y salud de todos los subsistemas.
./instalar.sh --test [--full]
```

> [!WARNING]
> **Aviso de Seguridad en Producción (Element Web)**: Durante la fase de desarrollo e integración, se han desactivado los avisos de cifrado de extremo a extremo (E2EE) y de copias de seguridad de claves (`UIFeature.keyBackup` y `UIFeature.crossSigning`) en `moodle-matrix-dev/element-config.json` para facilitar las pruebas del bot LLM sin fricción. Antes de desplegar el entorno en producción para la Universidad, se debe evaluar si se requiere E2EE estricto y, en tal caso, volver a activar estas variables.

## Funcionalidades del Bot en Matrix (OKF v0.1) {#funcionalidades_bot}
El Bot LLM implementa una ingesta automatizada siguiendo el estándar OKF v0.1 (`AGENTS.md`). Cuando se le envía un archivo, el bot genera una abstracción completa en el repositorio, creando:
- **Conceptos**: Conceptos abstractos extraídos.
- **Entidades**: Herramientas o personas mencionadas.
- **Recursos**: Resumen general del documento.

**Comandos del chat disponibles para el alumno:**
- **`!ayuda`** o **`!comandos`**: Despliega un menú informativo con los comandos.
- **`!deshacer`** o **`!revertir`**: Revierte la última ingesta automática en Git de manera segura.
- **`!sincronizar`** o **`!sync`**: Fuerza la actualización de tu repositorio con el material del profesor.

## Credenciales de Prueba {#credenciales_prueba}

Para probar el flujo de autenticación delegada (SSO) y la provisión de repositorios, se recomienda el uso de los siguientes usuarios de prueba (con los mismos datos de acceso en Moodle y Element):

| Usuario | Contraseña | Rol / Propósito |
|---------|------------|-----------------|
| `admin` | `adminpass123` | Administrador de plataforma Moodle / Creador de plantillas |
| `teacher1` | `Teacher1!` | Profesor del curso (gestión) |
| `student1` | `Student1!` | Estudiante de prueba principal (Repo Alumno #1) |
| `student2` | `Student2!` | Estudiante secundario para pruebas de concurrencia (Repo Alumno #2) |

> **Nota:** Se aconseja utilizar pestañas en modo incógnito al alternar entre `student1` y `student2` para evitar que Element re-cargue sesiones guardadas previas (localStorage) e impida el acceso cruzado.

## Inventario de Componentes y Carpetas Clave {#inventario_componentes}

| Carpeta / Fichero | Descripción |
|-------------------|-------------|
| `config/config.yaml` | Única Fuente de Verdad para configuración de puertos, LLM y proveedor Git. |
| `instalar.sh` | Orquestador principal de infraestructura y tests (`--test`). |
| `moodle-matrix-dev/mapeo-api/` | Microservicio FastAPI que maneja los mapeos Alumno <-> Git <-> Matrix. |
| `moodle-matrix-dev/mapeo-api/app/services/git/` | **(Fase 4.2)** Módulo de abstracción `GitProviderFactory` con implementaciones para GitHub, GitLab y Self-Hosted. |
| `moodle-matrix-dev/maubot/llm-wiki-assistant-plugin/` | Código fuente del bot Matrix. |
| `moodle-matrix-dev/maubot/llm-wiki-assistant-plugin/sync_worker/` | **(Fases 5.1 y 6)** Workers de RQ (Redis) encargados de la *Sincronización Ascendente* y el *Logging de Interacciones*. |
| `moodle-matrix-dev/maubot/llm-wiki-assistant-plugin/git_utils.py` | Módulo compartido de utilidades Git usado concurrentemente por Ingesta OKF, Sync, y Logging. Contiene el *Distributed Repo Lock*. |
| `moodle-matrix-dev/moodle_plugins/block_bdc/` | Plugin de Moodle que intercepta el inicio de sesión y llama a `mapeo-api`. |

## Fases de Implementación y Estado {#fases_implementacion}
- ✅ **Fase 0.1**: Documentación Doxygen y Configuración Base.
- ✅ **Fase 1**: Infraestructura Docker Compose.
- ✅ **Fase 2**: Almacén de Mapeos (FastAPI + SQLite).
- ✅ **Fase 3**: Bloque Moodle `block_bdc`.
- ✅ **Fase 4**: Provisionamiento de Repositorios y Pruebas de Integración.
- ✅ **Fase 4.2**: Refactorización de Proveedores Git (Factory / GitLab / Webhooks).
- ✅ **Fase 5**: Plugin Maubot (LLM, RAG, y Extracción OKF).
- ✅ **Fase 5.1**: Sincronización Ascendente (Upstream Sync).
- ✅ **Fase 6**: Registro de Interacciones y Distributed Locking (Redis).
- ✅ **Fase 7**: Orquestador de Pruebas Consolidado (`instalar.sh --test`) y control de regresiones.
- 🎯 **Fase 8**: Documentación Completa.
