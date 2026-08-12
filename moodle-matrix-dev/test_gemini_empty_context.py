import asyncio
import os
import sys

sys.path.append("/home/julia/llm-wiki-assistant/moodle-matrix-dev/maubot/llm-wiki-assistant-plugin")
from mixins.llm_clients import get_llm_client
import yaml

async def main():
    with open('/home/julia/llm-wiki-assistant/moodle-matrix-dev/config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    config['llm']['gemini']['api_key'] = os.environ.get('GEMINI_API_KEY')
    # Use standard client
    
    from mixins.llm_clients import GeminiClient
    client = GeminiClient(config['llm']['gemini'])
    
    system_prompt = """Eres un asistente docente. Tu función principal es responder preguntas
basándote EXCLUSIVAMENTE en el contexto recuperado de los ficheros OKF
del repositorio del alumno vinculado a esta sala. Puedes interactuar de
forma natural y educada (saludar, despedirte, etc.), pero cuando se te
pregunte por información de la asignatura o conceptos, debes seguir estas reglas:

Reglas estrictas:
1. Responde solo con información presente en el contexto recuperado.
   Si la información solicitada no aparece, dilo explícitamente con:
   'No he encontrado información sobre esto en tu repositorio.'

Contexto recuperado:
(No se encontró contexto detallado en el repositorio para esta consulta concreta)
"""
    user_prompt = "Pregunta: que sabes sobre el teorema de existencia y unicidad?"
    try:
        resp = await client.get_response(system_prompt, user_prompt)
        print("Response:", repr(resp))
    except Exception as e:
        print("Error:", e)

asyncio.run(main())
