"""Staging e produção no Railway. A diferença entre os dois vem só das variáveis."""

from .base import *  # noqa: F403
from .base import ALLOWED_HOSTS, env

DEBUG = False

# O healthcheck do Railway chama /healthz por HTTP com este host.
ALLOWED_HOSTS = [*ALLOWED_HOSTS, "healthcheck.railway.app"]

# O Railway termina o TLS e repassa o protocolo original neste cabeçalho.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_REDIRECT_EXEMPT = [r"^healthz$"]
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=31_536_000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = False
# Preload é compromisso permanente com o domínio; decidir quando o domínio próprio existir (D-29).
SILENCED_SYSTEM_CHECKS = ["security.W021"]

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_NAME = "__Host-sessionid"
CSRF_COOKIE_NAME = "__Host-csrftoken"
