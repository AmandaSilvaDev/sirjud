import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from apps.portfolio.models import Debtor
from apps.tenants.models import Cooperative

pytestmark = pytest.mark.django_db


@pytest.fixture
def cooperative():
    return Cooperative.objects.create(
        legal_name="Coop A", short_name="Coop A", cnpj="11.222.333/0001-81"
    )


def _debtor(cooperative, document="52998224725"):
    debtor = Debtor(cooperative=cooperative, name="Fulano")
    debtor.set_document(document)
    return debtor


def test_set_document_cifra_mascara_e_indexa(cooperative):
    debtor = _debtor(cooperative, "529.982.247-25")
    debtor.save()
    debtor.refresh_from_db()
    assert debtor.kind == Debtor.Kind.PERSON
    assert debtor.document_masked == "***.982.247-**"
    assert debtor.get_document() == "52998224725"
    assert "52998224725" not in debtor.document_encrypted
    assert Debtor.objects.get(document_hmac=Debtor.hash_document("52998224725")) == debtor


def test_cnpj_vira_pessoa_juridica(cooperative):
    assert _debtor(cooperative, "12.ABC.345/01DE-35").kind == Debtor.Kind.COMPANY


def test_documento_invalido_e_rejeitado(cooperative):
    with pytest.raises(ValidationError):
        _debtor(cooperative, "123.456.789-00")


def test_mesmo_cpf_nao_duplica_na_mesma_cooperativa(cooperative):
    _debtor(cooperative).save()
    with pytest.raises(IntegrityError):
        _debtor(cooperative).save()


def test_cooperativa_normaliza_cnpj(cooperative):
    assert cooperative.cnpj == "11222333000181"
