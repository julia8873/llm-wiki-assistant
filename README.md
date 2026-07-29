# LLM Wiki Assistant

[![Fase Actual](https://img.shields.io/badge/Estado-Fase_0.1_Completada-success.svg)](file:///c:/Users/vmira/Desktop/llm-wiki-assistant/docs/index.md)
[![MkDocs Material](https://img.shields.io/badge/Docs-MkDocs_Material-blue.svg)](file:///c:/Users/vmira/Desktop/llm-wiki-assistant/mkdocs.yml)
[![LLM Multi-Provider](https://img.shields.io/badge/LLM-OpenAI_|_Gemini_|_Ollama-blue.svg)](#)
[![Entrypoint](https://img.shields.io/badge/Entrypoint-instalar.sh-orange.svg)](#)
[![GitHub License](https://img.shields.io/badge/Licencia-MIT-green.svg)](#)

Entorno docente integrado que conecta **Moodle (LMS)**, **GitHub (Base de Conocimiento OKF)**, **Matrix/Element (Chat 1:1 por Alumno)** y **Maubot (LLM Wiki Assistant)** acotado a la Base de Conocimiento individual de cada estudiante.

---

## 📌 Propósito del Proyecto

El objetivo de este proyecto es proporcionar a cada estudiante de una asignatura una interfaz de chat inteligente en Matrix atendida por un bot de IA (**LLM Wiki Assistant**). El bot ayuda al estudiante a resolver dudas, analizar sus notas y consultar su trabajo almacenado en su propio repositorio GitHub en formato **Open Knowledge Format (OKF)**, clonado a partir de la plantilla maestro [`BdC-template`](https://github.com/julia8873/BdC-template).

### 🔒 Principio de Aislamiento Estricto por Alumno
- **Sin acceso externo**: El bot **únicamente** puede leer el contenido del repositorio fork de GitHub vinculado a la sala en la que está respondiendo.
- **Sin contaminación cruzada**: Jamás accederá a información de otros alumnos, repositorios externos ni buscadores web.

---

## 🛠️ Punto de Entrada Único: `instalar.sh`

Todas las operaciones del proyecto se ejecutan mediante el script raíz [`instalar.sh`](file:///c:/Users/vmira/Desktop/llm-wiki-assistant/instalar.sh). Nunca es necesario llamar a los scripts de `moodle-matrix-dev/scripts/` directamente.

```bash
./instalar.sh            # Muestra la ayuda completa
```

### Documentación (Fase 0.1)

```bash
# Levantar servidor local en http://localhost:8005
./instalar.sh docs serve

# Verificar sin warnings (mkdocs build --strict)
./instalar.sh docs check
```

### Entorno Docker Completo (Fase 1 — próximamente)

```bash
./instalar.sh up               # Levanta el stack completo
./instalar.sh down             # Para el stack conservando datos
./instalar.sh logs [servicio]  # Muestra logs
./instalar.sh status           # Estado de contenedores
```

---

## 🤖 Configuración del Proveedor LLM, Modelo y Base URL

El sistema admite múltiples proveedores de LLM de forma transparente desde [**`config/config.yaml`**](file:///c:/Users/vmira/Desktop/llm-wiki-assistant/config/config.yaml):

1. **OpenAI API** (Por defecto, soporta **TODOS** los modelos de OpenAI):
   - Modelo: `gpt-4o-mini` (o `gpt-4o`, `o3-mini`, `o1`, etc.).
   - API Base URL: `https://api.openai.com/v1` (o cualquier endpoint compatible como Azure OpenAI, vLLM, LM Studio).
2. **Google Gemini API**:
   - Modelo: `gemini-1.5-flash`.
   - API Base URL: `https://generativelanguage.googleapis.com/v1beta`.
3. **Ollama Local**:
   - Modelo: `llama3`.
   - URL Base: `http://localhost:11434`.

Para cambiar de proveedor o modelo, basta con modificar `llm.proveedor_activo` en [`config/config.yaml`](file:///c:/Users/vmira/Desktop/llm-wiki-assistant/config/config.yaml) sin tocar código.

---

## 🔄 Diferencias Clave

### 1. Respecto a `pluginMoodleMetricas`
En `pluginMoodleMetricas`, existía **un único repositorio compartido por asignatura**.

En **LLM Wiki Assistant**:
- Existe **un repositorio Fork por ALUMNO** (`https://github.com/julia8873/BdC-asignatura-alumno`).
- Existe **una sala de Matrix 1:1 por ALUMNO** vinculada a su fork.
- Se introduce una **tabla de mapeo central** (`mdl_block_bdc_mapping`):
  $$\text{Usuario Moodle} \iff \text{Asignatura Moodle} \iff \text{Fork GitHub} \iff \text{Sala Matrix 1:1}$$

### 2. Respecto al Subsistema Nativo de Moodle (`communication/provider/matrix`)
Moodle (4.2+) incluye un subsistema nativo de comunicación que crea **UNA sola sala compartida por CURSO** para todos los matriculados. 

El plugin [`block_bdc`](file:///c:/Users/vmira/Desktop/llm-wiki-assistant/block_bdc) **NO depende ni intercepta ese subsistema nativo**. Implementa su propio punto de acceso al chat, completamente independiente, capaz de resolver y vincular **una sala privada 1:1 por ALUMNO**.

---

## ⚙️ Configuración Única (`config/config.yaml`)

Todo el ecosistema (puertos Docker, nombres de contenedores, parámetros de GitHub, proveedor y modelo LLM, rutas OKF y timeouts) se configura desde un **único archivo**:

📄 [**`config/config.yaml`**](file:///c:/Users/vmira/Desktop/llm-wiki-assistant/config/config.yaml)

Cualquier otro componente (.env, maubot configs) lee o se deriva de este archivo para evitar duplicidad de valores.

---

## 🔐 Seguridad: Gestión de Credenciales

Ningún secreto (token, contraseña, clave privada) se sube al repositorio Git:

- Cada fichero con secretos tiene su plantilla versionada **`nombre.example`**.
- El fichero real correspondiente está excluido explícitamente en [`.gitignore`](file:///c:/Users/vmira/Desktop/llm-wiki-assistant/.gitignore).

| Archivo Real (Ignorado) | Archivo Plantilla (Versionado) | Propósito |
| :--- | :--- | :--- |
| `.env` | [`.env.example`](file:///c:/Users/vmira/Desktop/llm-wiki-assistant/.env.example) | Variables globales (`OPENAI_API_KEY`, `GEMINI_API_KEY`, DB pass, PAT GitHub) |
| `config/config.yaml` | [`config/config.yaml.example`](file:///c:/Users/vmira/Desktop/llm-wiki-assistant/config/config.yaml.example) | Configuración central del sistema |
| `moodle-matrix-dev/maubot/base-config.yaml` | [`moodle-matrix-dev/maubot/base-config.yaml.example`](file:///c:/Users/vmira/Desktop/llm-wiki-assistant/moodle-matrix-dev/maubot/base-config.yaml.example) | Config base servidor Maubot |
| `moodle-matrix-dev/maubot/config.yaml` | [`moodle-matrix-dev/maubot/config.yaml.example`](file:///c:/Users/vmira/Desktop/llm-wiki-assistant/moodle-matrix-dev/maubot/config.yaml.example) | Config instancia plugin Maubot |

---

## 🚀 Estado Actual y Hoja de Ruta (Fases)

### ✅ Fase 0: Estructura, Configuración Central y Documentación Base (COMPLETADA)
- Estructura completa de directorios (`config/`, `docs/`, `block_bdc/`, `moodle-matrix-dev/`, `tests/`).
- Archivo central `config/config.yaml` parametrizado para OpenAI (defecto), Gemini y Ollama.
- Plantillas `.example` para secretos y `.gitignore` actualizado.

---

### ✅ Fase 0.1: Documentación MkDocs (COMPLETADA)
- Configuración de `mkdocs.yml` con `mkdocs-material` y navegación a páginas con contenido real.
- Scripts de ejecución y comprobación (`moodle-matrix-dev/scripts/docs.sh serve` y `docs.sh check` con `mkdocs build --strict`).

---

### ⏳ Fases Pendientes

- [ ] **Fase 1: Infraestructura Docker Compose y Scripts de Instalación**
  - Ajuste de `docker-compose.yml` para incorporar Maubot y perfil opcional de Ollama.
  - Implementación de scripts modulares en `moodle-matrix-dev/scripts/`: `instalar.sh`, `configurar_git.sh`, `sincronizar_bot.sh`.
- [ ] **Fase 2: Desarrollo del Bloque Moodle `block_bdc` y Tabla de Mapeo**
  - Implementación del plugin de Moodle `block_bdc` (independiente del subsistema nativo de Moodle).
  - Creación del esquema de la tabla DB `mdl_block_bdc_mapping` en MariaDB.
  - Vistas e interfaz gráfica del bloque Moodle para profesores y alumnos.
- [ ] **Fase 3: Automatización de Forking y Sincronización Moodle-Matrix-GitHub**
  - Lógica de clonación automática del repo maestro `BdC-template` al matricular alumnos.
  - Creación automática de la sala Matrix 1:1 por alumno e inserción en la tabla de mapeo.
- [ ] **Fase 4: Suite de Pruebas Automáticas**
  - Tests unitarios y de integración para la tabla de mapeo y scripts de sincronización.
- [ ] **Fase 5: Plugin Maubot `llm-wiki-assistant` (Implementación del Bot)**
  - Implementación modular con arquitectura de `mixins/` (`matrix_handler`, `github_client`, `llm_client`, `moodle_mapper`).
  - Integración multi-proveedor: OpenAI (defecto), Gemini API y Ollama.
  - Validación del principio de lectura aislada al fork del alumno.

---

## 📚 Documentación

Para ver la documentación interactiva:

```bash
./moodle-matrix-dev/scripts/docs.sh serve
```
Navega a `http://localhost:8005`.
