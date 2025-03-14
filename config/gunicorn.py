# MIT License
#
# Copyright (c) 2025 Backblaze, Inc.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import multiprocessing
import os
from str2bool import str2bool


bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"

# Note - do NOT use preload_app - it causes issues with threading which cause crashes in Gunicorn

# Want a single process, so sessions are easy
workers = 1

threads = int(os.getenv("PYTHON_MAX_THREADS", multiprocessing.cpu_count() * 2))

print(f'Gunicorn configured with {threads} threads')

timeout = 300

reload = bool(str2bool(os.getenv("WEB_RELOAD", "false")))

loglevel = os.getenv('GUNICORN_LOGLEVEL', 'info').lower()
