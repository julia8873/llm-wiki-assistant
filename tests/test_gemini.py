import asyncio
import yaml
import os
import sys

sys.path.append("/home/julia/llm-wiki-assistant/moodle-matrix-dev/maubot/llm-wiki-assistant-plugin")
from mixins.llm_clients import get_llm_client

async def main():
    with open('/home/julia/llm-wiki-assistant/moodle-matrix-dev/config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    config['llm']['gemini']['api_key'] = os.environ.get('GEMINI_API_KEY')
    client = get_llm_client(config)
    
    system_prompt = "Eres un asistente. Contexto: vacio"
    user_prompt = "Pregunta: que sabes sobre el teorema de existencia y unicidad?"
    try:
        resp = await client.get_response(system_prompt, user_prompt)
        print("Response:", repr(resp))
    except Exception as e:
        print("Error:", e)

asyncio.run(main())
