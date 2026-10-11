import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.portfolio.models import Contract, ContractParty, Debtor
from apps.tenants.models import Branch, Cooperative, LawFirm

pytestmark = pytest.mark.django_db


def test_seed_demo_cria_dados_do_piloto():
    call_command("seed_demo")
    assert Cooperative.objects.count() == 1
    assert Branch.objects.count() == 5
    assert LawFirm.objects.count() == 2
    assert Contract.objects.count() == 200
    assert ContractParty.objects.exists()
    # O escritório de cobrança só recebe contratos em cobrança.
    cobranca = LawFirm.objects.get(short_name="Escritório Demo B")
    assert set(cobranca.contracts.values_list("stage", flat=True)) == {"in_collection"}


def test_seed_demo_nao_grava_cpf_em_texto_puro():
    call_command("seed_demo", contracts=10)
    for debtor in Debtor.objects.all():
        doc = debtor.get_document()
        assert doc not in debtor.document_encrypted
        assert doc not in debtor.document_masked
        assert debtor.document_hmac == Debtor.hash_document(doc)


def test_if_empty_nao_duplica():
    call_command("seed_demo", contracts=5)
    call_command("seed_demo", contracts=5, if_empty=True)
    assert Cooperative.objects.count() == 1
    assert Contract.objects.count() == 5


def test_proibido_em_producao(settings):
    settings.DJANGO_ENV = "production"
    with pytest.raises(CommandError):
        call_command("seed_demo")
    assert not Cooperative.objects.exists()


def test_predeploy_so_popula_no_staging(settings):
    settings.DJANGO_ENV = "production"
    call_command("predeploy")
    assert not Cooperative.objects.exists()
    settings.DJANGO_ENV = "staging"
    call_command("predeploy")
    assert Contract.objects.count() == 200
