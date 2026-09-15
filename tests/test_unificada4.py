import sys
import os
import subprocess
import datetime
import asyncio
from contextlib import asynccontextmanager

sys.path.append(os.path.abspath('/home/julia/llm-wiki-assistant/moodle-matrix-dev/maubot/llm-wiki-assistant-plugin'))
import sync_worker.tasks

@asynccontextmanager
async def mock_lock(*args, **kwargs):
    yield

sync_worker.tasks.distributed_repo_lock = mock_lock

from sync_worker.tasks import log_interaccion_unificada_task

def run(cmd):
    return subprocess.check_output(cmd, shell=True, text=True)

def main():
    repo_alumno_url = "https://github.com/fake-org/fake-repo4.git"
    official_repo_url = "https://github.com/fake-org/official-repo.git"
    
    import urllib.parse
    safe_name = urllib.parse.quote_plus(repo_alumno_url)
    destino_local = f"/tmp/llm_wiki_repos/{safe_name}"
    
    run(f"rm -rf {destino_local}")
    run(f"mkdir -p {destino_local}")
    run(f"git -C {destino_local} init")
    run(f"git -C {destino_local} commit --allow-empty -m 'Initial commit'")
    run(f"git -C {destino_local} remote add origin {repo_alumno_url}")
    
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
        "timestamp": datetime.datetime.now(datetime.UTC).isoformat() + "Z",
        "matrix_room_id": "!fake:matrix.org",
        "mensaje_alumno": "hola",
        "respuesta_bot": "adios",
        "tipo_interaccion": "solicitud_de_respuesta_directa",
        "concepto": ["saludo"]
    }
    
    print("Executing task...", flush=True)
    log_interaccion_unificada_task("!fake:matrix.org", repo_alumno_url, official_repo_url, log_data)
    
    print("--- GIT LOG ---", flush=True)
    print(run(f"git -C {destino_local} log --oneline -2"), flush=True)
    print("--- LINE COUNT ---", flush=True)
    fecha = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%d")
    print(f"File path: logs/interacciones/{fecha}.jsonl", flush=True)
    print(run(f"git -C {destino_local} show HEAD:logs/interacciones/{fecha}.jsonl | wc -l"), flush=True)
    print("--- JSONL CONTENT ---", flush=True)
    print(run(f"cat {destino_local}/logs/interacciones/{fecha}.jsonl"), flush=True)

if __name__ == "__main__":
    main()
