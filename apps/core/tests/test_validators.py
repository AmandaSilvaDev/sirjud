import pytest
from django.core.exceptions import ValidationError

from apps.core.validators import (
    format_document,
    is_valid_cnpj,
    is_valid_cpf,
    mask_document,
    normalize_cnj,
    validate_cpf_or_cnpj,
)


@pytest.mark.parametrize("cpf", ["529.982.247-25", "52998224725"])
def test_cpf_valido(cpf):
    assert is_valid_cpf(cpf)


@pytest.mark.parametrize("cpf", ["529.982.247-26", "111.111.111-11", "123", ""])
def test_cpf_invalido(cpf):
    assert not is_valid_cpf(cpf)


@pytest.mark.parametrize(
    "cnpj",
    [
        "11.222.333/0001-81",
        "12.ABC.345/01DE-35",  # exemplo oficial do CNPJ alfanumérico (Receita, 2026)
        "12abc34501de35",
    ],
)
def test_cnpj_valido(cnpj):
    assert is_valid_cnpj(cnpj)


@pytest.mark.parametrize("cnpj", ["11.222.333/0001-82", "12.ABC.345/01DE-36", "00000000000000"])
def test_cnpj_invalido(cnpj):
    assert not is_valid_cnpj(cnpj)


def test_validate_cpf_or_cnpj_rejeita_lixo():
    with pytest.raises(ValidationError):
        validate_cpf_or_cnpj("12345678900")


def test_mascara_e_formato():
    assert mask_document("52998224725") == "***.982.247-**"
    assert mask_document("11222333000181") == "**.222.333/****-**"
    assert format_document("52998224725") == "529.982.247-25"
    assert format_document("11222333000181") == "11.222.333/0001-81"


def test_cnj_valido_normaliza_formato():
    assert normalize_cnj("00012342020268220001") == "0001234-20.2026.8.22.0001"
    assert normalize_cnj("0001234-20.2026.8.22.0001") == "0001234-20.2026.8.22.0001"


@pytest.mark.parametrize("cnj", ["0001234-21.2026.8.22.0001", "123-45.2026.8.22.0001", "abc"])
def test_cnj_invalido(cnj):
    with pytest.raises(ValidationError):
        normalize_cnj(cnj)
