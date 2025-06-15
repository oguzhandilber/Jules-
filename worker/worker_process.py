import os
import sys
import redis
from rq import Worker, Queue, Connection

# Add project root to sys.path to allow importing soft_subtitle_remover
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from worker.soft_subtitle_remover import remove_soft_subtitles

listen = ['default']

REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

if __name__ == '__main__':
    try:
        conn = redis.Redis(host=REDIS_HOST, port=REDIS_PORT)
        conn.ping()
        print(f"Successfully connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
    except redis.exceptions.ConnectionError as e:
        print(f"Error: Could not connect to Redis at {REDIS_HOST}:{REDIS_PORT}.")
        print("Please ensure Redis server is running and accessible.")
        print(f"Details: {e}")
        sys.exit(1)

    with Connection(conn):
        worker = Worker(map(Queue, listen))
        print(f"RQ Worker started. Listening to queues: {', '.join(listen)}")
        worker.work(with_scheduler=True) # Added with_scheduler=True for potential future use, though not strictly needed now.
