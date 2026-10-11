from django.core.management import call_command


def test_collectstatic_de_producao_ignora_fonte_do_tailwind(settings, tmp_path):
    # Mesmo storage da produção: falha se algum CSS coletado apontar para arquivo inexistente.
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
    }
    settings.STATIC_ROOT = tmp_path

    call_command("collectstatic", "--noinput", verbosity=0)

    assert (tmp_path / "fonts" / "lato-latin-400-normal.woff2").exists()
    assert not (tmp_path / "src").exists()
