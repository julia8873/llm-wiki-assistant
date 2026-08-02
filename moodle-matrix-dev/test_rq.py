import redis
from rq import Queue
r = redis.Redis(host='redis', port=6379)
q = Queue('sync-jobs', connection=r)
job = q.enqueue('math.sqrt', 42, job_id='test-recovery-job-999')
print(f"Enqueued {job.id}")
