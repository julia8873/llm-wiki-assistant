# LLM Wiki Assistant

[![Fase Actual](https://img.shields.io/badge/Estado-Fase_1_Completada-success.svg)](file:///c:/Users/vmira/Desktop/llm-wiki-assistant/docs/index.md)
[![Doxygen](https://img.shields.io/badge/Docs-Doxygen-blue.svg)](file:///c:/Users/vmira/Desktop/llm-wiki-assistant/Doxyfile)
[![LLM Multi-Provider](https://img.shields.io/badge/LLM-OpenAI_|_Gemini_|_Ollama-blue.svg)](https://github.com/julia8873/llm-wiki-assistant)
[![Entrypoint](https://img.shields.io/badge/Entrypoint-instalar.sh-orange.svg)](https://github.com/julia8873/llm-wiki-assistant)
[![GitHub License](https://img.shields.io/badge/Licencia-MIT-green.svg)](https://github.com/julia8873/llm-wiki-assistant)

Sistema integrado de docencia Moodle-Matrix-GitHub. Proporciona a cada estudiante una interfaz de chat inteligente en Matrix, atendida por un agente LLM acotado estrictamente a la Base de Conocimiento individual (Fork) de dicho alumno.

## Comandos Operativos Base

> [!WARNING]
> **Aviso de Seguridad en Producción (Element Web)**: Durante la fase de desarrollo e integración, se han desactivado los avisos de cifrado de extremo a extremo (E2EE) y de copias de seguridad de claves (`UIFeature.keyBackup` y `UIFeature.crossSigning`) en `moodle-matrix-dev/element-config.json` para facilitar las pruebas del bot LLM sin fricción. Antes de desplegar el entorno en producción para la Universidad, se debe evaluar si se requiere E2EE estricto y, en tal caso, volver a activar estas variables.

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
```

## Credenciales de Prueba

Para probar el flujo de autenticación delegada (SSO) y la provisión de repositorios, se recomienda el uso de los siguientes usuarios de prueba (con los mismos datos de acceso en Moodle y Element):

| Usuario | Contraseña | Rol / Propósito |
|---------|------------|-----------------|
| `admin` | `adminpass123` | Administrador de plataforma Moodle / Creador de plantillas |
| `teacher1` | `Teacher1!` | Profesor del curso (gestión) |
| `student1` | `Student1!` | Estudiante de prueba principal (Fork #1) |
| `student2` | `Student2!` | Estudiante secundario para pruebas de concurrencia (Fork #2) |

> **Nota:** Se aconseja utilizar pestañas en modo incógnito al alternar entre `student1` y `student2` para evitar que Element re-cargue sesiones guardadas previas (localStorage) e impida el acceso cruzado.

## Arquitectura y Componentes

> El proyecto puede ejecutarse con el intérprete del sistema sin crear un entorno virtual. Para instalar las dependencias del microservicio, ejecuta:
>
> `cd moodle-matrix-dev/mapeo-api && python -m pip install -r requirements.txt`
- **Moodle (LMS)**: Orquestador de repositorios.
- **GitHub**: Almacenamiento OKF por alumno, con el PAT centralizado en `config/config.yaml` y propagado automáticamente a `GITHUB_PAT` por `instalar.sh` al generar [moodle-matrix-dev/.env](moodle-matrix-dev/.env).
- **Matrix/Synapse**: Servidor de chat 1:1.
- **Maubot**: Agente LLM aislado.

## Fases de Implementación
- ✅ **Fase 0.1**: Documentación Doxygen y Configuración Base.
- ✅ **Fase 1**: Infraestructura Docker Compose.
- ⏳ **Fase 2**: Bloque Moodle `block_bdc`.
- ⏳ **Fase 3**: Sincronización Moodle-Matrix-GitHub.
- ✅ **Fase 4**: Provisionamiento GitHub y Pruebas de Integración.
- ⏳ **Fase 5**: Plugin Maubot `llm-wiki-assistant`.

*Toda la documentación técnica se genera vía Doxygen. Ejecuta `./instalar.sh docs serve` para acceder a ella.*
