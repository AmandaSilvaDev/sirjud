import pytest
from cryptography.exceptions import InvalidTag
from django.core.exceptions import ImproperlyConfigured

from apps.core import crypto


@pytest.fixture(autouse=True)
def _limpa_cache_de_chaves():
    crypto._keyring.cache_clear()
    yield
    crypto._keyring.cache_clear()


def test_ida_e_volta():
    token = crypto.encrypt("52998224725", "ctx")
    assert token.startswith("t1:")
    assert "52998224725" not in token
    assert crypto.decrypt(token, "ctx") == "52998224725"


def test_nonce_aleatorio():
    assert crypto.encrypt("x", "ctx") != crypto.encrypt("x", "ctx")


def test_valor_copiado_para_outro_campo_nao_decifra():
    token = crypto.encrypt("52998224725", "portfolio.Debtor.document")
    with pytest.raises(InvalidTag):
        crypto.decrypt(token, "outro.campo")


def test_rotacao_decifra_com_chave_antiga(settings):
    antiga = settings.FIELD_ENCRYPTION_KEYS[1]
    settings.FIELD_ENCRYPTION_KEYS = [antiga]
    token = crypto.encrypt("segredo", "ctx")
    assert token.startswith("t0:")
    crypto._keyring.cache_clear()
    settings.FIELD_ENCRYPTION_KEYS = ["t2:" + crypto.generate_key(), antiga]
    assert crypto.decrypt(token, "ctx") == "segredo"


def test_chave_desconhecida():
    with pytest.raises(ValueError):
        crypto.decrypt("zz:AAAA", "ctx")


def test_chave_com_tamanho_errado(settings):
    settings.FIELD_ENCRYPTION_KEYS = ["k1:Y3VydGE="]
    with pytest.raises(ImproperlyConfigured):
        crypto.encrypt("x", "ctx")


def test_hmac_deterministico_e_dependente_da_chave(settings):
    a = crypto.search_hash("52998224725")
    assert a == crypto.search_hash("52998224725")
    assert len(a) == 64
    settings.SEARCH_HMAC_KEY = "outra-chave"
    assert crypto.search_hash("52998224725") != a
