# Plugin Bot Maubot (`llm-wiki-assistant-plugin`)

El bot es el componente encargado de atender las consultas de los estudiantes en sus salas 1:1 de Matrix.

## Estado de Implementación

> [!NOTE]
> **Estado Actual (Fase 0.1)**: El código funcional del bot aún no está implementado. Se desarrollará en la **Fase 5** del plan de trabajo.
> En esta fase se encuentra preparada la estructura base de carpetas en `moodle-matrix-dev/maubot/llm-wiki-assistant-plugin/` con el directorio `mixins/`.

## Principio de Aislamiento Estricto

En la Fase 5, el bot atenderá la sala y **únicamente** podrá leer y consultar información del repositorio fork de GitHub vinculado a la sala actual del alumno.

## Proveedores LLM Soportados

El bot integrará 3 proveedores intercambiables desde `config/config.yaml`:
1. **`openai`** (por defecto): API REST estándar de OpenAI (`gpt-4o-mini`, `gpt-4o`, etc.) o proxies compatibles.
2. **`gemini`**: API de Google Gemini (`gemini-1.5-flash`).
3. **`ollama`**: Inferencia local opcional.
