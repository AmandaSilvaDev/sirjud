"""Gera chaves novas para o .env local ou para as variáveis do Railway.

Usa só a biblioteca padrão: roda antes de existir .env e sem carregar o Django.
    py -3.12 scripts/generate_keys.py          (ou: uv run python scripts/generate_keys.py)
Não grava nada; só imprime. Gere valores diferentes para cada ambiente.
"""

import argparse
import base64
import os
import secrets


def generate(key_id: str = "k1") -> dict[str, str]:
    return {
        "DJANGO_SECRET_KEY": secrets.token_urlsafe(50),
        "FIELD_ENCRYPTION_KEYS": f"{key_id}:{base64.b64encode(os.urandom(32)).decode()}",
        "SEARCH_HMAC_KEY": secrets.token_urlsafe(48),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key-id", default="k1", help="Identificador da chave de campos.")
    args = parser.parse_args()
    for name, value in generate(args.key_id).items():
        print(f"{name}={value}")
    print(
        "\n# Atenção: perder FIELD_ENCRYPTION_KEYS = perder os CPFs/CNPJs cifrados."
        "\n# Guarde a chave de produção num cofre de senhas, fora do Railway."
    )


if __name__ == "__main__":
    main()
