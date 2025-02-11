command = '/home/sargent/spite/.spite/bin/gunicorn'
pythonpath = '/home/sargent/spite'
bind = 'unix:/home/sargent/spite/gunicorn.sock'
workers = 2
threads = 2
max_requests = 1000
max_requests_jitter = 50
worker_tmp_dir = '/dev/shm'
worker_class = 'gthread'
keepalive = 2  # Seconds to hold the connection open for reuse
worker_connections = 1000
timeout = 3600

