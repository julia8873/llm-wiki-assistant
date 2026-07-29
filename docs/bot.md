# Plugin Bot Maubot (`llm-wiki-assistant-plugin`)

## Estado de Implementación
El código fuente del bot aún no está implementado. Se desarrollará íntegramente en la **Fase 5**. 
Estructura base preparada en `moodle-matrix-dev/maubot/llm-wiki-assistant-plugin/`.

## Proveedores LLM Soportados
El sistema abstrae la capa de inferencia para permitir el intercambio en caliente mediante la configuración central `config/config.yaml`.

| Proveedor | API Base | Modelo Principal |
|---|---|---|
| **OpenAI** (Defecto) | `https://api.openai.com/v1` | `gpt-4o-mini` |
| **Gemini** | `generativelanguage.googleapis.com` | `gemini-1.5-flash` |
| **Ollama** | `http://localhost:11434` | `llama3` |

## Ciclo de Ejecución (Proyectado Fase 5)
1. **Trigger**: Recepción de mensaje en sala Matrix.
2. **Autorización**: Consulta a `mdl_block_bdc_mapping` para obtener URL del fork asignado a la sala.
3. **Lectura (RAG)**: Descarga/Indexación de archivos `.md` del fork.
4. **Inferencia**: Petición al proveedor LLM inyectando el contexto OKF.
5. **Respuesta**: Envío de salida a la sala Matrix.
