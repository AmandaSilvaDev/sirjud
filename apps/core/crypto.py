"""Criptografia de campos sensíveis (CPF/CNPJ, dados bancários).

- AES-256-GCM com nonce aleatório. O texto cifrado leva o id da chave na frente
  (`k1:...`) para permitir rotação: a primeira chave de FIELD_ENCRYPTION_KEYS
  cifra, todas decifram.
- `context` (ex.: "portfolio.Debtor.document") entra como dado associado: um
  valor cifrado copiado para outro campo não decifra.
- HMAC-SHA256 com chave separada, para busca exata sem decifrar.
"""

import base64
import hashlib
import hmac
import os
from functools import lru_cache

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

NONCE_SIZE = 12


@lru_cache(maxsize=1)
def _keyring() -> tuple[str, dict[str, bytes]]:
    entries = settings.FIELD_ENCRYPTION_KEYS
    if not entries:
        raise ImproperlyConfigured("FIELD_ENCRYPTION_KEYS não configurada.")
    keys: dict[str, bytes] = {}
    for entry in entries:
        key_id, sep, encoded = entry.strip().partition(":")
        if not sep or not key_id or ":" in encoded:
            raise ImproperlyConfigured("FIELD_ENCRYPTION_KEYS deve ter o formato id:chave_base64.")
        key = base64.b64decode(encoded)
        if len(key) != 32:
            raise ImproperlyConfigured(f"A chave '{key_id}' precisa ter 32 bytes (AES-256).")
        keys[key_id] = key
    active_id = entries[0].strip().partition(":")[0]
    return active_id, keys


def encrypt(plaintext: str, context: str) -> str:
    active_id, keys = _keyring()
    nonce = os.urandom(NONCE_SIZE)
    ciphertext = AESGCM(keys[active_id]).encrypt(nonce, plaintext.encode(), context.encode())
    return f"{active_id}:{base64.b64encode(nonce + ciphertext).decode()}"


def decrypt(token: str, context: str) -> str:
    _, keys = _keyring()
    key_id, _, encoded = token.partition(":")
    if key_id not in keys:
        raise ValueError("Valor cifrado com chave desconhecida.")
    raw = base64.b64decode(encoded)
    nonce, ciphertext = raw[:NONCE_SIZE], raw[NONCE_SIZE:]
    return AESGCM(keys[key_id]).decrypt(nonce, ciphertext, context.encode()).decode()


def search_hash(value: str) -> str:
    """HMAC-SHA256 em hexadecimal, para colunas de busca exata."""
    key = settings.SEARCH_HMAC_KEY
    if not key:
        raise ImproperlyConfigured("SEARCH_HMAC_KEY não configurada.")
    return hmac.new(key.encode(), value.encode(), hashlib.sha256).hexdigest()


def generate_key() -> str:
    """Gera uma chave AES-256 em base64 (usada pelo comando generate_keys)."""
    return base64.b64encode(os.urandom(32)).decode()
