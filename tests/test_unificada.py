import sys
import os
import datetime
sys.path.append(os.path.abspath('moodle-matrix-dev/maubot/llm-wiki-assistant-plugin'))
from sync_worker.tasks import log_interaccion_unificada_task

def main():
    repo_alumno_url = "https://github.com/fake-org/fake-repo.git"
    official_repo_url = "https://github.com/fake-org/official-repo.git"
    
    import urllib.parse
    safe_name = urllib.parse.quote_plus(repo_alumno_url)
    destino_local = f"/tmp/llm_wiki_repos/{safe_name}"
    
    os.system(f"rm -rf {destino_local}")
    os.system(f"mkdir -p {destino_local}")
    os.system(f"git init {destino_local}")
    os.system(f"git -C {destino_local} commit --allow-empty -m 'Initial commit'")
    os.system(f"git -C {destino_local} remote add origin {repo_alumno_url}")
    
    import sync_worker.tasks
    original_run_git = sync_worker.tasks.run_git_command
    async def mock_run_git(*args, **kwargs):
        if args[0] == 'push' or args[0] == 'fetch':
            return 0, "", ""
        return await original_run_git(*args, **kwargs)
    sync_worker.tasks.run_git_command = mock_run_git
    
    class MockMapeo:
        async def post_evento(self, *args, **kwargs):
            pass
    sync_worker.tasks.get_mapeo_client = lambda: MockMapeo()
    
    async def mock_asegurar(*args, **kwargs):
        pass
    sync_worker.tasks.asegurar_repo_local = mock_asegurar
    
    log_data = {
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "matrix_room_id": "!fake:matrix.org",
        "mensaje_alumno": "hola",
        "respuesta_bot": "adios",
        "tipo_interaccion": "solicitud_de_respuesta_directa",
        "concepto": ["saludo"],
        "ficheros_consultados": [],
        "git_provider": "github"
    }
    
    # We call the synchronous wrapper
    log_interaccion_unificada_task("!fake:matrix.org", repo_alumno_url, official_repo_url, log_data)
    
    print("--- GIT LOG ---")
    os.system(f"git -C {destino_local} log --oneline -2")
    print("--- LINE COUNT ---")
    fecha = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    os.system(f"git -C {destino_local} show HEAD:logs/interacciones/{fecha}.jsonl | wc -l")
    print("--- JSONL CONTENT ---")
    os.system(f"cat {destino_local}/logs/interacciones/{fecha}.jsonl")
    
main()
