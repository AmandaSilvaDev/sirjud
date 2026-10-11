from unittest import mock

import pytest
from django.db import OperationalError
from django.urls import reverse

pytestmark = pytest.mark.django_db


def test_healthz_ok(client):
    response = client.get(reverse("core:healthz"))
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
    assert "no-cache" in response["Cache-Control"]


def test_healthz_banco_fora_responde_503(client):
    with mock.patch("apps.core.views.connection.cursor", side_effect=OperationalError):
        response = client.get(reverse("core:healthz"))
    assert response.status_code == 503


def test_healthz_so_aceita_get(client):
    assert client.post(reverse("core:healthz")).status_code == 405


def test_home_tem_cabecalhos_de_seguranca(client):
    response = client.get(reverse("core:home"))
    assert response.status_code == 200
    assert response["X-Frame-Options"] == "DENY"
    assert response["X-Content-Type-Options"] == "nosniff"
    csp = response["Content-Security-Policy"]
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "unsafe-inline" not in csp


def test_home_em_portugues(client):
    response = client.get(reverse("core:home"))
    assert 'lang="pt-BR"' in response.content.decode()
