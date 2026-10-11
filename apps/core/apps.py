from django.apps import AppConfig
from django.contrib.staticfiles.apps import StaticFilesConfig


class CoreConfig(AppConfig):
    name = "apps.core"
    verbose_name = "Núcleo"


class SirjudStaticFilesConfig(StaticFilesConfig):
    # static/src/ é a fonte do Tailwind (vira static/css/app.css no build) e não vai
    # para produção: o @import "tailwindcss" quebra o collectstatic do whitenoise.
    ignore_patterns = [*StaticFilesConfig.ignore_patterns, "src"]
