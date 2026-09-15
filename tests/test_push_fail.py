import subprocess

script = """
import redis
from rq import Queue
from sync_worker.tasks import log_interaction_task
from datetime import datetime, timezone

r = redis.Redis(host='redis', port=6379)
q = Queue('log-jobs', connection=r)

log_data = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "matrix_room_id": "!MkqEOSzSkHgqXxQqIo:localhost",
    "mensaje_alumno": "test de fallo de push",
    "respuesta_bot": "simulado",
    "ficheros_consultados": [],
    "git_provider": "github"
}
job = q.enqueue(
    log_interaction_task,
    "!MkqEOSzSkHgqXxQqIo:localhost",
    "https://github.com/julia8873/AA-student1.git",
    "https://github.com/julia8873/AA-Oficial.git",
    log_data
)
print(f'Job enqueued: {job.id}')
"""

subprocess.run(['docker', 'exec', 'moodle-matrix-dev-sync-worker-2', 'python', '-c', script])
