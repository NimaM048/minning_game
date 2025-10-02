# utils/lock.py

import redis
import logging
from contextlib import contextmanager
import time

r = redis.Redis(host="localhost", port=6379, db=0, decode_responses=True)

@contextmanager
def redis_lock(key: str, timeout: int = 60, retry_delay: float = 0.1, max_retries: int = 3):
    try:
        retries = 0
        while retries < max_retries:
            locked = r.set(name=key, value="locked", nx=True, ex=timeout)
            if locked:
                logging.info(f"[REDIS LOCK] Lock for '{key}' acquired.")
                try:
                    yield True
                finally:
                    try:
                        r.delete(key)
                        logging.info(f"[REDIS LOCK] Lock for '{key}' released.")
                    except Exception as e:
                        logging.error(f"[REDIS LOCK] Failed to release lock for '{key}': {e}")
                return
            else:
                logging.info(f"[REDIS LOCK] Lock for '{key}' is held by another process, retrying...")
                retries += 1
                time.sleep(retry_delay)
        logging.warning(f"[REDIS LOCK] Could not acquire lock for '{key}' after {max_retries} retries.")
        yield False
    except redis.exceptions.ConnectionError as e:
        logging.error(f"[REDIS LOCK] Redis connection error: {e}")
        yield False
