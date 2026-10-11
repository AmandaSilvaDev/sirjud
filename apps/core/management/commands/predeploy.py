"""Pre-deploy do Railway: aplica migrations e, só no staging, popula dados fictícios."""

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Roda antes de cada deploy: migrate (+ seed_demo --if-empty no staging)."

    def handle(self, *args, **options):
        call_command("migrate", interactive=False)
        if settings.DJANGO_ENV == "staging":
            call_command("seed_demo", if_empty=True)
