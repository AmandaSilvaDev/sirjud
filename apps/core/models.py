from django.db import models


class TimeStampedModel(models.Model):
    """Base de todas as tabelas: quando foi criado e quando mudou pela última vez.

    `updated_at` é indexado para a carga incremental da API de BI (RF-121).
    """

    created_at = models.DateTimeField("criado em", auto_now_add=True)
    updated_at = models.DateTimeField("alterado em", auto_now=True, db_index=True)

    class Meta:
        abstract = True


class MoneyField(models.DecimalField):
    """Valor em reais. Sempre Decimal, nunca float."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_digits", 14)
        kwargs.setdefault("decimal_places", 2)
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if kwargs.get("max_digits") == 14:
            del kwargs["max_digits"]
        if kwargs.get("decimal_places") == 2:
            del kwargs["decimal_places"]
        return name, path, args, kwargs
