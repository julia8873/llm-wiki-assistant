import subprocess
import time
import threading

def run_worker():
    script = '''import asyncio
from git_utils import distributed_repo_lock
async def main():
    async with distributed_repo_lock('fake_heartbeat_test'):
        print('Lock acquired. Sleeping 70s...')
        await asyncio.sleep(70)
        print('Done.')
asyncio.run(main())'''
    subprocess.run(['docker', 'exec', 'moodle-matrix-dev-sync-worker-1', 'python', '-c', script])

t = threading.Thread(target=run_worker)
t.start()
time.sleep(5)
for i in range(8):
    res = subprocess.run(['docker', 'exec', 'moodle-matrix-dev-redis-1', 'redis-cli', 'TTL', 'repo_lock:fake_heartbeat_test'], capture_output=True, text=True)
    print(f'Check {i+1}: TTL = {res.stdout.strip()}')
    time.sleep(10)

t.join()
print('Finished.')

