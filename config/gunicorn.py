import multiprocessing
import os
from str2bool import str2bool


bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

preload_app = True

# Want a single process, so sessions are easy
workers = 1
# workers = int(os.getenv("WEB_CONCURRENCY", multiprocessing.cpu_count() * 2))

# threads = 1
threads = int(os.getenv("PYTHON_MAX_THREADS", multiprocessing.cpu_count() * 2))

print(f'Gunicorn configured with {threads} threads')

timeout = 300

reload = bool(str2bool(os.getenv("WEB_RELOAD", "false")))

loglevel = os.getenv('GUNICORN_LOGLEVEL', 'info').lower()
