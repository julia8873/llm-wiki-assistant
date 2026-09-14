# LLM Wiki Assistant

![Fase Actual](https://img.shields.io/badge/Estado-Fase_7_Completada-success.svg)
[![Doxygen](https://img.shields.io/badge/Docs-Doxygen-blue.svg)](Doxyfile)
[![LLM Multi-Provider](https://img.shields.io/badge/LLM-OpenAI_|_Gemini_|_Ollama-blue.svg)](config/config.yaml)
[![Entrypoint](https://img.shields.io/badge/Entrypoint-instalar.sh-orange.svg)](instalar.sh)

Sistema integrado de docencia Moodle-Matrix-Git. Proporciona a cada estudiante una interfaz de chat inteligente en Matrix, atendida por un agente LLM acotado estrictamente a la Base de Conocimiento individual de dicho alumno (generada desde un template oficial del profesor).

*Toda la documentación técnica completa se genera vía Doxygen. Ejecuta `./instalar.sh docs serve` para acceder a ella en [http://localhost:8005](http://localhost:8005).*

## Tabla de Contenidos
- [Guía de Instalación y Puesta en Marcha](#paso_a_paso)
- [Comandos Operativos Base (Desarrollo)](#comandos_base)
- [Funcionalidades del Bot en Matrix (OKF v0.1)](#funcionalidades_bot)
- [Credenciales de Prueba](#credenciales_prueba)
- [Inventario de Componentes y Carpetas Clave](#inventario_componentes)
- Fases de Implementación y Estado

## Guía de Instalación y Puesta en Marcha {#paso_a_paso}

Sigue estos pasos para iniciar el proyecto. El orquestador principal te guiará durante el proceso y generará las plantillas de configuración automáticamente.

### Paso 0: Descripción de Servicios

Los servicios que se deben levantar son: Moodle para el CMS y MariaDB, Matrix(Synapse) y Element para de chat. Si los servicios no están desplegados en un entorno, esta tarea la lleva a cabo el docker-compose.yml disponible en la carpeta: 
   moodle-matrix-dev 
donde hay un docker-compose.yml que levantará dichos servicios en contenedores cuando ejecutemos el script de instalación:
   
   instalar.sh

Para dar servicio desde fuera, se recomienda configurar proxy inverso (nginx, traefic, caddy, etc.) que securice la conexión y derive el tráfico al mapeo de puerto del contenedor correspondiente. 
   TODO: Vea ejemplos de configuración en la carpeta /reverse-proxy-confs

TODO: Describir los archivos de configuración de las carpetas y servicios



### Paso 1: Copiar los ficheros de entorno
Copiar .env.example y rellenar los valores.
(Si se va a usar ollama, cambiar OLLAMA_PORT=puerto_Ollama_CHANGE_ME y llm-wiki-assistant/moodle-matrix-dev/.env modificar OLLAMA_PORT)


```bash
./instalar.sh
```

### Paso 2: Completar Credenciales

1. **`config/config.yaml`**:
   - `git.proveedor_activo` y `git.organizacion`: Tu proveedor para crear los repositorios de alumnos (GitHub, GitLab, etc).
   - `git.github.pat`: Tu token personal si usas GitHub (con permisos de `repo`).
   - `llm.proveedor_activo`: Indica el motor de IA (`openai`, `gemini`, `ollama`).
   - Cambiar la variable api_base_url 

### Paso 3: Aplicar Configuración
Una vez hayas introducido tus tokens y claves, vuelve a lanzar el orquestador. Aplicará los cambios en todo el sistema:
```bash
./instalar.sh up
```

### Paso 4: Desplegar el Bot (Maubot)

1. Accede a [http://localhost:29317/_matrix/maubot/](http://localhost:29317/_matrix/maubot/) e inicia sesión (`admin` / tu `MAUBOT_ADMIN_PASSWORD`).
2. **Plugins:** Sube el archivo local ubicado en `moodle-matrix-dev/maubot/llm-wiki-assistant-plugin/plugin.mbp`.
3. **Clients:** Añade un cliente con User ID `@llm_wiki_bot:localhost`, Homeserver `http://synapse:8008`, y pega el **Token del bot** que te imprimió `./instalar.sh` en la consola (deja la contraseña en blanco).
4. **Instances:** Crea una nueva instancia vinculando el Cliente y el Plugin que acabas de subir.

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

**Comandos del chat disponibles para el alumno:**
- **`!ayuda`** o **`!comandos`**: Despliega un menú informativo con los comandos.
- **`!deshacer`** o **`!revertir`**: Revierte la última ingesta automática en Git de manera segura.
- **`!sincronizar`** o **`!sync`**: Fuerza la actualización de tu repositorio con el material del profesor.

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


