# LLM Wiki Assistant

Sistema integrado de docencia Moodle-Matrix-Git.

## Tabla de Contenidos
- [Paso 0: Descripción de Servicios](#paso-0-descripción-de-servicios)
- [Paso 1: Levantar el entorno base](#paso-1-levantar-el-entorno-base)
- [Paso 2: Completar Credenciales (Hardening para Producción)](#paso-2-completar-credenciales-hardening-para-producción)
- [Paso 3: Aplicar Configuración](#paso-3-aplicar-configuración)
- [Paso 4: Desplegar el Bot (Maubot)](#paso-4-desplegar-el-bot-maubot)
- [Comandos Operativos Base (Desarrollo)](#comandos_base)
- [Funcionalidades del Bot en Matrix (OKF v0.1)](#funcionalidades_bot)
- [Credenciales de Prueba](#credenciales_prueba)
- [Inventario de Componentes y Carpetas Clave](#inventario_componentes)

### Paso 0: Descripción de Servicios

Los servicios que se deben levantar son: Moodle para el CMS y MariaDB, Matrix(Synapse) y Element para de chat. Si los servicios no están desplegados en un entorno, esta tarea la lleva a cabo el docker-compose.yml disponible en la carpeta: 
   moodle-matrix-dev 
donde hay un docker-compose.yml que levantará dichos servicios en contenedores cuando ejecutemos el script de instalación:
   
   instalar.sh

Para dar servicio desde fuera, se recomienda configurar proxy inverso (nginx, traefic, caddy, etc.) que securice la conexión y derive el tráfico al mapeo de puerto del contenedor correspondiente. 
   TODO: Vea ejemplos de configuración en la carpeta /reverse-proxy-confs

TODO: Describir los archivos de configuración de las carpetas y servicios


### Paso 1: Levantar el entorno base
Ejecuta el script principal por primera vez. Levantará la infraestructura inicial e imprimirá un panel interactivo con las credenciales que faltan por configurar.
```bash
./instalar.sh
```

### Paso 2: Completar Credenciales

1. **`.env`** (en la raíz):
   - **Contraseñas de Bases de Datos:** `MARIADB_ROOT_PASSWORD`, `MARIADB_PASSWORD`, `POSTGRES_PASSWORD`.
   - **Contraseñas de Administrador:** `MOODLE_PASSWORD`, `SYNAPSE_ADMIN_PASSWORD`, `MAUBOT_ADMIN_PASSWORD`. 
   - **Claves Criptográficas:** `MAUBOT_CRYPTO_PICKLE_KEY`. 
   - **Tokens de APIs Internas:** `MAPEO_API_TOKEN`. Puedes dejarlo en `changeme` para que se genere uno automáticamente.
   - **Proveedores de IA:** `OPENAI_API_KEY` o `GEMINI_API_KEY`.
   - **MATRIX_ACCESS_TOKEN:** Token de administrador. Para obtenerlo la primera vez: abre Element, inicia sesión con tu `SYNAPSE_ADMIN_USER` y la contraseña que hayas definido. Ve a **Ajustes -> Ayuda e información -> Avanzado -> Token de acceso**, cópialo y pégalo aquí.

2. **`config/config.yaml`**:
   - **Proveedor Git:** En `git.proveedor_activo` pon `github` o `gitlab`. Configura tu `organizacion` (donde se crearán los repositorios) y el `pat` (Personal Access Token) con permisos plenos de creación de repositorios (`repo` en GitHub).
   - **Proveedor LLM:** En `llm.proveedor_activo` define tu motor (`openai`, `gemini`, `ollama`) y si es necesario ajusta el modelo a utilizar en sus respectivas secciones.

### Paso 3: Aplicar Configuración
Una vez hayas introducido tus tokens y claves, vuelve a lanzar el orquestador. Aplicará los cambios en todo el sistema:
```bash
./instalar.sh up
```

### Paso 4: Desplegar el Bot (Maubot)
El script de instalación ya empaquetó tu bot, pero debes registrarlo en el motor de bots:
1. Accede a [http://localhost:29317/_matrix/maubot/](http://localhost:29317/_matrix/maubot/) e inicia sesión (`admin` / tu `MAUBOT_ADMIN_PASSWORD`).
2. **Plugins:** Sube el archivo local ubicado en `src/bot/llm-wiki-assistant-plugin/plugin.mbp`.
3. **Clients:** Añade un cliente con User ID `@llm_wiki_bot:localhost`, Homeserver `http://synapse:8008`, y pega el **Token del bot** que te imprimió `./instalar.sh` en la consola (deja la contraseña en blanco).
4. **Instances:** Crea una nueva instancia vinculando el Cliente y el Plugin que acabas de subir.

¡Listo! El bot ya estará escuchando en la red Matrix para ser invitado automáticamente a las salas de los alumnos.

## Comandos 
```bash
# Instalación base y levantamiento de servidor de documentación Doxygen
./instalar.sh

# Levantar infraestructura Docker Compose
./instalar.sh up [--ollama]

# Levantar servidor de documentación
./instalar.sh docs serve

# Verificación estricta de documentación
./instalar.sh docs check

# Ejecutar Batería de Tests Consolidada
./instalar.sh --test [--full]
```

## Funcionalidades del Bot en Matrix

**Comandos del chat disponibles para el alumno:**
- **`!ayuda`** o **`!comandos`**: Despliega un menú informativo con los comandos.
- **`!deshacer`** o **`!revertir`**: Revierte la última ingesta automática en Git de manera segura.
- **`!sincronizar`** o **`!sync`**: Fuerza la actualización de tu repositorio con el material del profesor.

## Inventario de Componentes

| Carpeta / Fichero | Descripción |
|-------------------|-------------|
| `config/config.yaml` | Única Fuente de Verdad para configuración de puertos, LLM y proveedor Git. |
| `instalar.sh` | Orquestador principal de infraestructura y tests (`--test`). |
| `src/api/` | Microservicio FastAPI que maneja los mapeos Alumno <-> Git <-> Matrix. |
| `src/api/app/services/git/` | **(Fase 4.2)** Módulo de abstracción `GitProviderFactory` con implementaciones para GitHub, GitLab y Self-Hosted. |
| `src/bot/llm-wiki-assistant-plugin/` | Código fuente del bot Matrix. |
| `src/bot/llm-wiki-assistant-plugin/sync_worker/` | **(Fases 5.1 y 6)** Workers de RQ (Redis) encargados de la *Sincronización Ascendente* y el *Logging de Interacciones*. |
| `src/bot/llm-wiki-assistant-plugin/git_utils.py` | Módulo compartido de utilidades Git usado concurrentemente por Ingesta OKF, Sync, y Logging. Contiene el *Distributed Repo Lock*. |
| `src/moodle/block_bdc/` | Plugin de Moodle que intercepta el inicio de sesión y llama a `mapeo-api`. |

