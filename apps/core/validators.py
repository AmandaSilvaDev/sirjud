"""Validação e formatação de CPF, CNPJ e número CNJ."""

import re

from django.core.exceptions import ValidationError

_CNPJ_WEIGHTS_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
_CNPJ_WEIGHTS_2 = [6, *_CNPJ_WEIGHTS_1]
_CNJ_RE = re.compile(r"^(\d{7})-?(\d{2})\.?(\d{4})\.?(\d)\.?(\d{2})\.?(\d{4})$")


def only_document_chars(value: str) -> str:
    """Remove pontuação. Mantém letras porque o CNPJ alfanumérico (2026) tem letras."""
    return re.sub(r"[^0-9A-Za-z]", "", value or "").upper()


def _cpf_digit(digits: str) -> int:
    total = sum(int(d) * w for d, w in zip(digits, range(len(digits) + 1, 1, -1), strict=True))
    rest = total % 11
    return 0 if rest < 2 else 11 - rest


def is_valid_cpf(value: str) -> bool:
    cpf = only_document_chars(value)
    if not re.fullmatch(r"\d{11}", cpf) or cpf == cpf[0] * 11:
        return False
    return _cpf_digit(cpf[:9]) == int(cpf[9]) and _cpf_digit(cpf[:10]) == int(cpf[10])


def _cnpj_digit(chars: str, weights: list[int]) -> int:
    # No CNPJ alfanumérico, cada caractere vale (código ASCII − 48): "0"=0 … "9"=9, "A"=17…
    total = sum((ord(c) - 48) * w for c, w in zip(chars, weights, strict=True))
    rest = total % 11
    return 0 if rest < 2 else 11 - rest


def is_valid_cnpj(value: str) -> bool:
    cnpj = only_document_chars(value)
    if not re.fullmatch(r"[0-9A-Z]{12}\d{2}", cnpj) or cnpj == cnpj[0] * 14:
        return False
    first = _cnpj_digit(cnpj[:12], _CNPJ_WEIGHTS_1)
    second = _cnpj_digit(cnpj[:12] + str(first), _CNPJ_WEIGHTS_2)
    return cnpj[12:] == f"{first}{second}"


def validate_cpf_or_cnpj(value: str) -> None:
    doc = only_document_chars(value)
    if len(doc) == 11 and is_valid_cpf(doc):
        return
    if len(doc) == 14 and is_valid_cnpj(doc):
        return
    raise ValidationError("CPF ou CNPJ inválido.", code="invalid_document")


def validate_cnpj(value: str) -> None:
    if not is_valid_cnpj(value):
        raise ValidationError("CNPJ inválido.", code="invalid_cnpj")


def format_document(value: str) -> str:
    doc = only_document_chars(value)
    if len(doc) == 11:
        return f"{doc[:3]}.{doc[3:6]}.{doc[6:9]}-{doc[9:]}"
    if len(doc) == 14:
        return f"{doc[:2]}.{doc[2:5]}.{doc[5:8]}/{doc[8:12]}-{doc[12:]}"
    return doc


def mask_document(value: str) -> str:
    """CPF: ***.456.789-** · CNPJ: **.345.678/****-** (para listas e painéis)."""
    doc = only_document_chars(value)
    if len(doc) == 11:
        return f"***.{doc[3:6]}.{doc[6:9]}-**"
    if len(doc) == 14:
        return f"**.{doc[2:5]}.{doc[5:8]}/****-**"
    return "***"


def _cnj_check_digits(seq: str, year: str, segment: str, court: str, origin: str) -> int:
    return 98 - (int(f"{seq}{year}{segment}{court}{origin}00") % 97)


def normalize_cnj(value: str) -> str:
    """Valida o número CNJ (módulo 97, Res. CNJ 65/2008) e devolve no formato padrão.

    Formato: NNNNNNN-DD.AAAA.J.TR.OOOO
    """
    match = _CNJ_RE.match((value or "").strip())
    if not match:
        raise ValidationError(
            "Número CNJ deve ter o formato NNNNNNN-DD.AAAA.J.TR.OOOO.", code="invalid_cnj"
        )
    seq, dv, year, segment, court, origin = match.groups()
    if int(dv) != _cnj_check_digits(seq, year, segment, court, origin):
        raise ValidationError("Dígito verificador do número CNJ não confere.", code="invalid_cnj")
    return f"{seq}-{dv}.{year}.{segment}.{court}.{origin}"


def validate_cnj(value: str) -> None:
    normalize_cnj(value)
