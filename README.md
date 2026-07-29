# LLM Wiki Assistant

[![Fase Actual](https://img.shields.io/badge/Estado-Fase_0.1_Completada-success.svg)](file:///c:/Users/vmira/Desktop/llm-wiki-assistant/docs/index.md)
[![Doxygen](https://img.shields.io/badge/Docs-Doxygen-blue.svg)](file:///c:/Users/vmira/Desktop/llm-wiki-assistant/Doxyfile)
[![LLM Multi-Provider](https://img.shields.io/badge/LLM-OpenAI_|_Gemini_|_Ollama-blue.svg)](https://github.com/julia8873/llm-wiki-assistant)
[![Entrypoint](https://img.shields.io/badge/Entrypoint-instalar.sh-orange.svg)](https://github.com/julia8873/llm-wiki-assistant)
[![GitHub License](https://img.shields.io/badge/Licencia-MIT-green.svg)](https://github.com/julia8873/llm-wiki-assistant)

Sistema integrado de docencia Moodle-Matrix-GitHub. Proporciona a cada estudiante una interfaz de chat inteligente en Matrix, atendida por un agente LLM acotado estrictamente a la Base de Conocimiento individual (Fork) de dicho alumno.

## Comandos Operativos Base

Único punto de entrada: `instalar.sh`.

```bash
# Instalación base y levantamiento de servidor de documentación Doxygen
./instalar.sh

# Levantar servidor de documentación (puerto 8005)
./instalar.sh docs serve

# Verificación estricta de documentación (Falla ante warnings)
./instalar.sh docs check
```

## Arquitectura y Componentes
- **Moodle (LMS)**: Orquestador de repositorios.
- **GitHub**: Almacenamiento OKF por alumno.
- **Matrix/Synapse**: Servidor de chat 1:1.
- **Maubot**: Agente LLM aislado.

## Fases de Implementación
- ✅ **Fase 0.1**: Documentación Doxygen y Configuración Base.
- ⏳ **Fase 1**: Infraestructura Docker Compose.
- ⏳ **Fase 2**: Bloque Moodle `block_bdc`.
- ⏳ **Fase 3**: Sincronización Moodle-Matrix-GitHub.
- ⏳ **Fase 4**: Pruebas Automáticas.
- ⏳ **Fase 5**: Plugin Maubot `llm-wiki-assistant`.

*Toda la documentación técnica se genera vía Doxygen. Ejecuta `./instalar.sh docs serve` para acceder a ella.*
