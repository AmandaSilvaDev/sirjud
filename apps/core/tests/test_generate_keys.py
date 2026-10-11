import base64
from io import StringIO

from django.core.management import call_command


def test_generate_keys_imprime_chaves_validas():
    out = StringIO()
    call_command("generate_keys", key_id="k9", stdout=out)
    lines = dict(line.split("=", 1) for line in out.getvalue().splitlines() if "=" in line)
    key_id, _, key = lines["FIELD_ENCRYPTION_KEYS"].partition(":")
    assert key_id == "k9"
    assert len(base64.b64decode(key)) == 32
    assert len(lines["DJANGO_SECRET_KEY"]) >= 50
    assert len(lines["SEARCH_HMAC_KEY"]) >= 32
