"""Gera chaves novas para colar nas variáveis do Railway. Não grava nada."""

import secrets

from django.core.management.base import BaseCommand
from django.core.management.utils import get_random_secret_key

from apps.core.crypto import generate_key


class Command(BaseCommand):
    help = "Imprime valores novos para DJANGO_SECRET_KEY, FIELD_ENCRYPTION_KEYS e SEARCH_HMAC_KEY."

    def add_arguments(self, parser):
        parser.add_argument("--key-id", default="k1", help="Identificador da chave de campos.")

    def handle(self, *args, key_id, **options):
        self.stdout.write(f"DJANGO_SECRET_KEY={get_random_secret_key()}")
        self.stdout.write(f"FIELD_ENCRYPTION_KEYS={key_id}:{generate_key()}")
        self.stdout.write(f"SEARCH_HMAC_KEY={secrets.token_urlsafe(48)}")
        self.stdout.write(
            self.style.WARNING(
                "Gere valores diferentes para staging e produção. "
                "Perder FIELD_ENCRYPTION_KEYS = perder os CPFs cifrados."
            )
        )
