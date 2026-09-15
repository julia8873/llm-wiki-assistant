import subprocess
import time

script = """
import redis
from rq import Queue, Retry
from sync_worker.tasks import log_interaction_task, sync_repo_task
from datetime import datetime, timezone

r = redis.Redis(host='redis', port=6379)
q_sync = Queue('sync-jobs', connection=r)
q_log = Queue('log-jobs', connection=r)

# 1. Tarea sync
job_sync = q_sync.enqueue(
    sync_repo_task,
    "!MkqEOSzSkHgqXxQqIo:localhost",
    "https://github.com/julia8873/AA-student1.git",
    "https://github.com/julia8873/AA-Oficial.git",
    retry=Retry(max=3, interval=5)
)
print(f"Sync job: {job_sync.id}")

# 2. Tarea log
log_data = {
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "matrix_room_id": "!MkqEOSzSkHgqXxQqIo:localhost",
    "mensaje_alumno": "race condition test with retry on both",
    "respuesta_bot": "simulado",
    "ficheros_consultados": [],
    "git_provider": "github"
}
job_log = q_log.enqueue(
    log_interaction_task,
    kwargs={
        "matrix_room_id": "!MkqEOSzSkHgqXxQqIo:localhost",
        "repo_alumno_url": "https://github.com/julia8873/AA-student1.git",
        "official_repo_url": "https://github.com/julia8873/AA-Oficial.git",
        "log_data": log_data
    },
    retry=Retry(max=3, interval=5)
)
print(f"Log job: {job_log.id}")
"""

print("Enqueueing both tasks simultaneously...")
subprocess.run(['docker', 'exec', 'moodle-matrix-dev-sync-worker-1', 'python', '-c', script])

print("Tailing logs for 25 seconds to observe LockAcquisitionError and subsequent retry on both...")
p1 = subprocess.Popen(['docker', 'logs', '--tail=0', '-f', 'moodle-matrix-dev-sync-worker-1'])
p2 = subprocess.Popen(['docker', 'logs', '--tail=0', '-f', 'moodle-matrix-dev-sync-worker-2'])
time.sleep(25)
p1.terminate()
p2.terminate()
