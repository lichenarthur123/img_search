import threading
from rembg import remove, new_session

# Read-Write Lock for global variable
class ReadWriteLock:
    def __init__(self):
        self._read_ready = threading.Condition(threading.Lock())
        self._readers = 0

    def acquire_read(self):
        with self._read_ready:
            self._readers += 1

    def release_read(self):
        with self._read_ready:
            self._readers -= 1
            if not self._readers:
                self._read_ready.notify_all()

    def acquire_write(self):
        self._read_ready.acquire()
        while self._readers > 0:
            self._read_ready.wait()

    def release_write(self):
        self._read_ready.release()

    def __enter__(self):
        self.acquire_write()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release_write()

# Initialize Read-Write Lock
global_lock = ReadWriteLock()
global_variable = {}
api_key = ''
with open("api_key.txt", "r") as f:
    api_key = f.read().strip()
rembg_session = new_session()