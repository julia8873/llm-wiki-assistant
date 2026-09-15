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
    client = get_llm_client(config)
    
    system_prompt = config['llm']['system_prompt']
    
    # Simulating what assistant.py does
    system_prompt_with_context = f"{system_prompt}\n\n"
    
    # We simulate 5 chunks from the vector DB based on the actual logs we saw
    system_prompt_with_context += "Contexto recuperado:\n"
    system_prompt_with_context += """--- Chunk 1 (Fichero: profesores/profesor1/okf/sources/ugr-ed2-prueba-20220404.md) ---
### Ejercicio 5: Unicidad de Soluciones mediante Operadores Contractivos
La función $F : [-1, 1] \times \mathbb{R} \to \mathbb{R}$, $(t, x) \mapsto F(t, x)$ es continua y cumple la condición de Lipschitz:
$$|F(t, x_1) - F(t, x_2)| \le L|x_1 - x_2|, \quad \forall (t, x) \in [-1, 1] \times \mathbb{R},$$
con $L < \\frac{1}

"""
    
    user_prompt = "Pregunta: que sabes sobre el teorema de existencia y unicidad?"
    
    try:
        resp = await client.get_response(system_prompt_with_context, user_prompt)
        print("Response:", repr(resp))
    except Exception as e:
        print("Error:", e)

asyncio.run(main())
