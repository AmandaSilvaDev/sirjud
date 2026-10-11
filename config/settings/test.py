"""Testes (pytest). Chaves fixas e falsas; banco PostgreSQL (local ou serviço do CI)."""

import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-only-secret-key-not-for-production")
os.environ.setdefault("DATABASE_URL", "postgres://sirjud:sirjud@127.0.0.1:5432/sirjud")
# Chaves de teste (32 bytes em base64). Nunca usar fora dos testes.
os.environ.setdefault(
    "FIELD_ENCRYPTION_KEYS",
    "t1:dGVzdC1rZXktMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=,"
    "t0:b2xkLXRlc3Qta2V5LTAwMDAwMDAwMDAwMDAwMDAwMDA=",
)
os.environ.setdefault("SEARCH_HMAC_KEY", "test-only-hmac-key")

from .base import *  # noqa: F403

DJANGO_ENV = "test"
ALLOWED_HOSTS = ["testserver", "localhost"]

# Hash rápido nos testes; produção usa os hashers do base (Argon2 entra na Fase 1).
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
