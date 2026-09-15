from redis import Redis
from rq import Queue
import sync_worker.tasks as tasks

redis = Redis(host='redis', port=6379)
q = Queue('log-jobs', connection=redis)
q.enqueue(tasks.log_interaccion_extraccion_task, "room_1", "https://github.com/julia8873/e2e-test-repo.git", "url_1", {"concepto": "test"})
print("Job enqueued")
