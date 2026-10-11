import base64
import importlib.util
from pathlib import Path

from django.conf import settings

SCRIPT = Path(settings.BASE_DIR) / "scripts" / "generate_keys.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("generate_keys", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generate_keys_gera_chaves_validas():
    keys = _load_script().generate("k9")
    key_id, _, key = keys["FIELD_ENCRYPTION_KEYS"].partition(":")
    assert key_id == "k9"
    assert len(base64.b64decode(key)) == 32
    assert len(keys["DJANGO_SECRET_KEY"]) >= 50
    assert len(keys["SEARCH_HMAC_KEY"]) >= 32


def test_generate_keys_nao_repete_valores():
    script = _load_script()
    assert script.generate() != script.generate()
