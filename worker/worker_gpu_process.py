import os
import sys
import redis
from rq import Worker, Queue, Connection

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

listen = ['hard_caption_queue']

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

if __name__ == '__main__':
    try:
        conn = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
        conn.ping()
        print(f"GPU Worker successfully connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
    except redis.exceptions.ConnectionError as e:
        print(f"GPU Worker Error: Could not connect to Redis at {REDIS_HOST}:{REDIS_PORT}.")
        print(f"Details: {e}")
        sys.exit(1)

    with Connection(conn):
        print(f"Starting GPU RQ Worker. Listening to queues: {', '.join(listen)}")
        print("Ensure this worker runs in a GPU-enabled environment if jobs require it.")
        # For GPU workers, often a specific worker class or settings might be needed
        # depending on how GPU resources are managed (e.g. preloading models on GPU).
        # For now, using the standard Worker class.
        worker = Worker(map(Queue, listen))
        worker.work() # Consider adding with_scheduler=True if you plan to use RQ Scheduler
