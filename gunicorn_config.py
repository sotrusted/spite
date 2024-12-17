command = '/home/sargent/spite/.spite/bin/gunicorn'
pythonpath = '/home/sargent/spite'
bind = 'unix:/home/sargent/spite/gunicorn.sock'
workers = 3 
keepalive = 2  # Seconds to hold the connection open for reuse
worker_class = 'gevent'
worker_connections = 1000
timeout = 3600

