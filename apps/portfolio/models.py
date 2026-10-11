"""Carteira: devedores e contratos vindos do core bancário.

Fase 0 cria o mínimo para o seed_demo. Garantias, importação, valor recuperado
e histórico de atribuição entram na Fase 3.
"""

from django.db import models
from django.utils import timezone

from apps.core import crypto
from apps.core.models import MoneyField, TimeStampedModel
from apps.core.validators import mask_document, only_document_chars, validate_cpf_or_cnpj


class Product(TimeStampedModel):
    cooperative = models.ForeignKey(
        "tenants.Cooperative", on_delete=models.PROTECT, related_name="products"
    )
    code = models.CharField("código", max_length=30)
    name = models.CharField("nome", max_length=120)

    class Meta:
        verbose_name = "produto"
        verbose_name_plural = "produtos"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["cooperative", "code"], name="uniq_product_code_per_cooperative"
            )
        ]

    def __str__(self):
        return self.name


class Debtor(TimeStampedModel):
    """Pessoa ou empresa devedora, avalista ou garantidora.

    O CPF/CNPJ nunca fica em texto puro: `document_encrypted` (AES-256-GCM),
    `document_hmac` para busca exata e `document_masked` para listas.
    Use `set_document()`; não preencha esses campos à mão.
    """

    class Kind(models.TextChoices):
        PERSON = "PF", "Pessoa física"
        COMPANY = "PJ", "Pessoa jurídica"

    ENCRYPTION_CONTEXT = "portfolio.Debtor.document"

    cooperative = models.ForeignKey(
        "tenants.Cooperative", on_delete=models.PROTECT, related_name="debtors"
    )
    kind = models.CharField("tipo", max_length=2, choices=Kind.choices)
    name = models.CharField("nome", max_length=200)
    document_encrypted = models.TextField("CPF/CNPJ (cifrado)", editable=False)
    document_hmac = models.CharField("CPF/CNPJ (HMAC)", max_length=64, editable=False)
    document_masked = models.CharField("CPF/CNPJ (mascarado)", max_length=20, editable=False)
    city = models.CharField("município", max_length=120, blank=True)
    state = models.CharField("UF", max_length=2, blank=True)

    class Meta:
        verbose_name = "devedor"
        verbose_name_plural = "devedores"
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["cooperative", "document_hmac"], name="uniq_debtor_document_per_cooperative"
            )
        ]

    def __str__(self):
        return f"{self.name} ({self.document_masked})"

    @staticmethod
    def hash_document(raw: str) -> str:
        return crypto.search_hash(only_document_chars(raw))

    def set_document(self, raw: str) -> None:
        validate_cpf_or_cnpj(raw)
        doc = only_document_chars(raw)
        self.kind = self.Kind.PERSON if len(doc) == 11 else self.Kind.COMPANY
        self.document_encrypted = crypto.encrypt(doc, self.ENCRYPTION_CONTEXT)
        self.document_hmac = crypto.search_hash(doc)
        self.document_masked = mask_document(doc)

    def get_document(self) -> str:
        """CPF/CNPJ completo. A partir da Fase 2, toda chamada vinda de tela é auditada."""
        return crypto.decrypt(self.document_encrypted, self.ENCRYPTION_CONTEXT)


class Contract(TimeStampedModel):
    """Contrato de crédito inadimplente (o crédito; o processo judicial é outra entidade)."""

    class Stage(models.TextChoices):
        AVAILABLE = "available", "Disponível"
        IN_COLLECTION = "in_collection", "Em cobrança extrajudicial"
        AWAITING_ACCEPTANCE = "awaiting_acceptance", "Aguardando aceite"
        PENDING_DOCUMENTS = "pending_documents", "Com pendência documental"
        AWAITING_FILING = "awaiting_filing", "Aguardando ajuizamento"
        JUDICIAL = "judicial", "Judicial"
        SETTLED = "settled", "Baixado – pago"
        WRITTEN_OFF = "written_off", "Baixado – perda"
        RETURNED = "returned", "Devolvido à cooperativa"

    cooperative = models.ForeignKey(
        "tenants.Cooperative", on_delete=models.PROTECT, related_name="contracts"
    )
    branch = models.ForeignKey(
        "tenants.Branch", on_delete=models.PROTECT, related_name="contracts", verbose_name="agência"
    )
    product = models.ForeignKey(
        Product, on_delete=models.PROTECT, related_name="contracts", verbose_name="produto"
    )
    debtor = models.ForeignKey(
        Debtor, on_delete=models.PROTECT, related_name="contracts", verbose_name="cooperado"
    )
    number = models.CharField("nº do contrato", max_length=40)
    external_id = models.CharField("id no core", max_length=60, blank=True)
    original_amount = MoneyField("valor original")
    balance = MoneyField("saldo devedor")
    balance_date = models.DateField("data do saldo")
    overdue_since = models.DateField("vencimento da parcela mais antiga em atraso")
    signed_at = models.DateField("data da contratação", null=True, blank=True)
    stage = models.CharField(
        "situação", max_length=24, choices=Stage.choices, default=Stage.AVAILABLE, db_index=True
    )
    law_firm = models.ForeignKey(
        "tenants.LawFirm",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="contracts",
        verbose_name="escritório responsável",
    )
    last_activity_at = models.DateTimeField("última atualização", null=True, blank=True)

    class Meta:
        verbose_name = "contrato"
        verbose_name_plural = "contratos"
        ordering = ["-overdue_since"]
        constraints = [
            models.UniqueConstraint(
                fields=["cooperative", "number"], name="uniq_contract_number_per_cooperative"
            ),
            models.CheckConstraint(
                condition=models.Q(balance__gte=0), name="contract_balance_gte_0"
            ),
        ]
        indexes = [models.Index(fields=["cooperative", "stage"])]

    def __str__(self):
        return self.number

    @property
    def days_overdue(self) -> int:
        return max((timezone.localdate() - self.overdue_since).days, 0)


class ContractParty(TimeStampedModel):
    """Pessoas ligadas ao contrato além do devedor principal (avalistas, fiadores…)."""

    class Role(models.TextChoices):
        DEBTOR = "debtor", "Devedor"
        GUARANTOR = "guarantor", "Avalista"
        SURETY = "surety", "Fiador"
        COLLATERAL_PROVIDER = "collateral_provider", "Garantidor"
        SPOUSE = "spouse", "Cônjuge"

    cooperative = models.ForeignKey(
        "tenants.Cooperative", on_delete=models.PROTECT, related_name="+"
    )
    contract = models.ForeignKey(Contract, on_delete=models.CASCADE, related_name="parties")
    debtor = models.ForeignKey(Debtor, on_delete=models.PROTECT, related_name="party_roles")
    role = models.CharField("papel", max_length=24, choices=Role.choices)

    class Meta:
        verbose_name = "parte do contrato"
        verbose_name_plural = "partes do contrato"
        constraints = [
            models.UniqueConstraint(
                fields=["contract", "debtor", "role"], name="uniq_party_role_per_contract"
            )
        ]

    def __str__(self):
        return f"{self.get_role_display()}: {self.debtor.name}"
