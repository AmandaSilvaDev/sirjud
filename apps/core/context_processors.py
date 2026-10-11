from django.conf import settings


def environment(request):
    """Expõe o ambiente para os templates (faixa "Ambiente de testes" no staging)."""
    return {"DJANGO_ENV": settings.DJANGO_ENV}
