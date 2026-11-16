import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
workers = 1
worker_class = "gthread"
threads = 2
timeout = 60
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
worker_tmp_dir = "/tmp"
control_socket_disable = True
accesslog = "-"
errorlog = "-"
loglevel = "info"
