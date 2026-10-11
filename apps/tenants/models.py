"""Cooperativas (tenants), agências e escritórios.

Membership, Engagement (vínculo cooperativa × escritório), tribunais, comarcas e
feriados entram na Fase 1, junto com o escopo de acesso.
"""

from django.db import models

from apps.core.models import TimeStampedModel
from apps.core.validators import only_document_chars, validate_cnpj


class Cooperative(TimeStampedModel):
    """Cooperativa singular: o tenant. Todo dado de negócio aponta para uma."""

    legal_name = models.CharField("razão social", max_length=200)
    short_name = models.CharField("nome curto", max_length=80)
    cnpj = models.CharField("CNPJ", max_length=14, unique=True, validators=[validate_cnpj])
    is_active = models.BooleanField("ativa", default=True)

    class Meta:
        verbose_name = "cooperativa"
        verbose_name_plural = "cooperativas"
        ordering = ["short_name"]

    def __str__(self):
        return self.short_name

    def save(self, *args, **kwargs):
        self.cnpj = only_document_chars(self.cnpj)
        super().save(*args, **kwargs)


class Branch(TimeStampedModel):
    """Agência (posto de atendimento) da cooperativa."""

    cooperative = models.ForeignKey(
        Cooperative, on_delete=models.PROTECT, related_name="branches", verbose_name="cooperativa"
    )
    code = models.CharField("código", max_length=20)
    name = models.CharField("nome", max_length=120)
    city = models.CharField("município", max_length=120)
    state = models.CharField("UF", max_length=2)

    class Meta:
        verbose_name = "agência"
        verbose_name_plural = "agências"
        ordering = ["cooperative", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["cooperative", "code"], name="uniq_branch_code_per_cooperative"
            )
        ]

    def __str__(self):
        return f"{self.code} · {self.name}"


class LawFirm(TimeStampedModel):
    """Escritório de advocacia parceiro.

    É global (atende várias cooperativas). O que ele pode ver em cada
    cooperativa depende do vínculo e do que estiver atribuído a ele.
    """

    legal_name = models.CharField("razão social", max_length=200)
    short_name = models.CharField("nome curto", max_length=80)
    cnpj = models.CharField("CNPJ", max_length=14, unique=True, validators=[validate_cnpj])
    oab_registration = models.CharField("registro OAB da sociedade", max_length=30, blank=True)
    offers_litigation = models.BooleanField("ajuizamento", default=False)
    offers_collection = models.BooleanField("cobrança extrajudicial", default=False)
    offers_passive = models.BooleanField("polo passivo", default=False)
    is_active = models.BooleanField("ativo", default=True)

    class Meta:
        verbose_name = "escritório"
        verbose_name_plural = "escritórios"
        ordering = ["short_name"]

    def __str__(self):
        return self.short_name

    def save(self, *args, **kwargs):
        self.cnpj = only_document_chars(self.cnpj)
        super().save(*args, **kwargs)
