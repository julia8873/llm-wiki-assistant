import asyncio
import os
import sys

sys.path.append("/data/llm-wiki-assistant-plugin")
from mixins.llm_clients import get_llm_client
from mixins.repo_reader import RepoReader
from mixins.vector_store import VectorStore
import yaml

async def main():
    with open('/config/config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    config['llm']['gemini']['api_key'] = os.environ.get('GEMINI_API_KEY')
    client = get_llm_client(config)
    
    pg_user = os.environ.get("PGVECTOR_USER", "llm_wiki")
    pg_pass = os.environ.get("PGVECTOR_PASSWORD", "llm_wiki_pass")
    pg_db = os.environ.get("PGVECTOR_DB", "vector_store")
    pg_host = os.environ.get("PGVECTOR_HOST", "pgvector")
    dsn = f"postgresql://{pg_user}:{pg_pass}@{pg_host}:5432/{pg_db}"
    vector_store = VectorStore(dsn)
    await vector_store.connect()
    
    repo_reader = RepoReader(config, vector_store, client)
    
    mapeo_data = {
        'repo_url': 'https://github.com/julia8873/EDII-Oficial.git',
        'is_teacher': True,
        'teacher_mode': 'carpeta',
        'moodle_username': 'profesor1'
    }
    
    query = "que sabes sobre el teorema de existencia y unicidad?"
    results = await repo_reader.search(mapeo_data, query, limit=5)
    
    system_prompt_with_context = f"{config['llm']['system_prompt']}\n\n"
    
    repo_files = await vector_store.get_all_files(mapeo_data['repo_url'])
    if repo_files:
        system_prompt_with_context += "Lista de todos los ficheros disponibles en este repositorio:\n- " + "\n- ".join(repo_files) + "\n\n"

    system_prompt_with_context += "Contexto recuperado:\n"
    if not results:
        system_prompt_with_context += "(No se encontró contexto detallado en el repositorio para esta consulta concreta)\n"
    else:
        for i, chunk in enumerate(results):
            system_prompt_with_context += f"--- Chunk {i+1} (Fichero: {chunk['file_path']}) ---\n{chunk['content']}\n\n"
            
    user_prompt = f"Pregunta: {query}"
    
    print("=== SYSTEM PROMPT ===")
    print(system_prompt_with_context)
    print("=====================")
    
    try:
        resp = await client.get_response(system_prompt_with_context, user_prompt)
        print("Response:", repr(resp))
    except Exception as e:
        print("Error:", e)

    await vector_store.close()

asyncio.run(main())
