"""Configuração do gunicorn no Railway. PORT é fornecida pelo Railway."""

import os

# "[::]" aceita IPv4 e IPv6 (a rede privada do Railway usa IPv6).
bind = f"[::]:{os.environ.get('PORT', '8000')}"
workers = int(os.environ.get("WEB_CONCURRENCY", "2"))
threads = int(os.environ.get("GUNICORN_THREADS", "4"))
timeout = 60
graceful_timeout = 30
max_requests = 1000
max_requests_jitter = 100
accesslog = "-"
errorlog = "-"
forwarded_allow_ips = "*"
# Sem socket de controle (gunicornc): não usamos, e o padrão ($HOME/.gunicorn)
# não é gravável pelo usuário sem privilégios da imagem.
control_socket_disable = True
