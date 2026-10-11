from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView


@never_cache
@require_GET
def healthz(request):
    """Healthcheck do Railway: confirma que o app responde e alcança o banco."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        return JsonResponse({"status": "erro", "database": "indisponível"}, status=503)
    return JsonResponse({"status": "ok", "database": "ok"})


class HomeView(TemplateView):
    """Página pública provisória. Vira a tela de login na Fase 1."""

    template_name = "core/home.html"
