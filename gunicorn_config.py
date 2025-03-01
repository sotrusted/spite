import multiprocessing
command = '/home/sargent/spite/.spite/bin/gunicorn'
pythonpath = '/home/sargent/spite'
bind = 'unix:/home/sargent/spite/gunicorn.sock'
workers = multiprocessing.cpu_count() * 2 
threads = 2
max_requests = 1000
max_requests_jitter = 50
worker_class = 'gthread'
keepalive = 5  # Seconds to hold the connection open for reuse
umask = 0o002  # Add this to ensure socket has correct permissions


worker_connections = 1000
timeout = 3600

# Memory management
max_requests = 1000
max_requests_jitter = 100
worker_tmp_dir = '/dev/shm'

# Logging
loglevel = 'debug'
capture_output = True
accesslog = '/home/sargent/spite/logs/gunicorn_access.log'
errorlog = '/home/sargent/spite/logs/gunicorn_error.log'
loglevel = 'info'
