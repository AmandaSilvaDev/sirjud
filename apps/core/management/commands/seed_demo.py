"""Popula o banco com dados fictícios (Faker pt_BR) para staging e desenvolvimento.

Nunca roda em produção. Uso:
    python manage.py seed_demo              # cria os dados
    python manage.py seed_demo --if-empty   # só se o banco estiver vazio (staging)
"""

import random
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from faker import Faker

from apps.core.validators import is_valid_cnpj, is_valid_cpf, only_document_chars
from apps.portfolio.models import Contract, ContractParty, Debtor, Product
from apps.tenants.models import Branch, Cooperative, LawFirm

BRANCHES = [
    ("0001", "Sede", "Porto Velho"),
    ("0002", "Ji-Paraná", "Ji-Paraná"),
    ("0003", "Ariquemes", "Ariquemes"),
    ("0004", "Vilhena", "Vilhena"),
    ("0005", "Cacoal", "Cacoal"),
]

PRODUCTS = [
    ("RURAL", "Crédito rural"),
    ("GIRO", "Capital de giro"),
    ("FIN", "Financiamento"),
    ("CONSIG", "Consignado"),
    ("CARTAO", "Cartão"),
    ("PESSOAL", "Crédito pessoal"),
]

# (situação, peso, escritório: "A" ajuizamento, "B" cobrança, None sem escritório)
STAGE_MIX = [
    (Contract.Stage.AVAILABLE, 15, None),
    (Contract.Stage.IN_COLLECTION, 25, "B"),
    (Contract.Stage.AWAITING_ACCEPTANCE, 5, "A"),
    (Contract.Stage.AWAITING_FILING, 5, "A"),
    (Contract.Stage.JUDICIAL, 45, "A"),
    (Contract.Stage.SETTLED, 5, None),
]


class Command(BaseCommand):
    help = "Cria dados fictícios: cooperativa, agências, 2 escritórios e contratos."

    def add_arguments(self, parser):
        parser.add_argument("--contracts", type=int, default=200)
        parser.add_argument("--seed", type=int, default=42)
        parser.add_argument(
            "--if-empty", action="store_true", help="Não faz nada se já houver cooperativa."
        )

    def handle(self, *args, contracts, seed, if_empty, **options):
        if settings.DJANGO_ENV == "production":
            raise CommandError("seed_demo é proibido em produção.")
        if if_empty and Cooperative.objects.exists():
            self.stdout.write("Banco já tem dados; seed_demo ignorado.")
            return

        self.fake = Faker("pt_BR")
        self.fake.seed_instance(seed)
        self.rng = random.Random(seed)  # noqa: S311 — dados fictícios, não é uso criptográfico

        with transaction.atomic():
            cooperative = self._cooperative()
            branches = self._branches(cooperative)
            products = self._products(cooperative)
            firms = self._law_firms()
            total = self._contracts(cooperative, branches, products, firms, contracts)

        self.stdout.write(
            self.style.SUCCESS(
                f"Criados: 1 cooperativa, {len(branches)} agências, {len(firms)} escritórios, "
                f"{total} contratos."
            )
        )

    def _cnpj(self) -> str:
        while True:
            cnpj = only_document_chars(self.fake.cnpj())
            if is_valid_cnpj(cnpj):
                return cnpj

    def _cooperative(self):
        return Cooperative.objects.create(
            legal_name="Cooperativa de Crédito Demonstração Vale do Madeira",
            short_name="Coop Demo Vale do Madeira",
            cnpj=self._cnpj(),
        )

    def _branches(self, cooperative):
        return [
            Branch.objects.create(
                cooperative=cooperative, code=code, name=name, city=city, state="RO"
            )
            for code, name, city in BRANCHES
        ]

    def _products(self, cooperative):
        return [
            Product.objects.create(cooperative=cooperative, code=code, name=name)
            for code, name in PRODUCTS
        ]

    def _law_firms(self):
        litigation = LawFirm.objects.create(
            legal_name=f"{self.fake.last_name()} & {self.fake.last_name()} Advogados (demo)",
            short_name="Escritório Demo A",
            cnpj=self._cnpj(),
            oab_registration=f"RO {self.rng.randint(100, 999)}",
            offers_litigation=True,
            offers_passive=True,
        )
        collection = LawFirm.objects.create(
            legal_name=f"{self.fake.last_name()} Cobrança e Advocacia (demo)",
            short_name="Escritório Demo B",
            cnpj=self._cnpj(),
            oab_registration=f"RO {self.rng.randint(100, 999)}",
            offers_collection=True,
        )
        return {"A": litigation, "B": collection}

    def _new_debtor(self, cooperative, used_hmacs: set[str]) -> Debtor:
        is_company = self.rng.random() < 0.2
        while True:
            raw = self.fake.cnpj() if is_company else self.fake.cpf()
            valid = is_valid_cnpj(raw) if is_company else is_valid_cpf(raw)
            if valid and Debtor.hash_document(raw) not in used_hmacs:
                break
        debtor = Debtor(
            cooperative=cooperative,
            name=self.fake.company() if is_company else self.fake.name(),
            city=self.rng.choice(BRANCHES)[2],
            state="RO",
        )
        debtor.set_document(raw)
        used_hmacs.add(debtor.document_hmac)
        return debtor

    def _money(self, low: int, high: int) -> Decimal:
        return Decimal(self.rng.randint(low * 100, high * 100)) / 100

    def _contracts(self, cooperative, branches, products, firms, count) -> int:
        used_hmacs: set[str] = set()
        debtors = [self._new_debtor(cooperative, used_hmacs) for _ in range(int(count * 0.9))]
        Debtor.objects.bulk_create(debtors)
        guarantors = [self._new_debtor(cooperative, used_hmacs) for _ in range(count // 4)]
        Debtor.objects.bulk_create(guarantors)

        today = timezone.localdate()
        now = timezone.now()
        stages = [s for s, _, _ in STAGE_MIX]
        weights = [w for _, w, _ in STAGE_MIX]
        firm_by_stage = {s: f for s, _, f in STAGE_MIX}

        contracts = []
        for i in range(count):
            stage = self.rng.choices(stages, weights)[0]
            firm_key = firm_by_stage[stage]
            original = (
                self._money(5_000, 1_200_000)
                if self.rng.random() < 0.15
                else self._money(3_000, 250_000)
            )
            overdue_since = today - timedelta(days=self.rng.randint(60, 1500))
            year = overdue_since.year - self.rng.randint(0, 3)
            contracts.append(
                Contract(
                    cooperative=cooperative,
                    branch=self.rng.choice(branches),
                    product=self.rng.choice(products),
                    debtor=debtors[i % len(debtors)],
                    number=f"CT-{year}-{i + 1:04d}",
                    external_id=f"CORE{self.rng.randint(10**7, 10**8 - 1)}",
                    original_amount=original,
                    balance=(original * Decimal(self.rng.uniform(0.5, 1.4))).quantize(
                        Decimal("0.01")
                    ),
                    balance_date=today,
                    overdue_since=overdue_since,
                    signed_at=overdue_since - timedelta(days=self.rng.randint(90, 1800)),
                    stage=stage,
                    law_firm=firms[firm_key] if firm_key else None,
                    last_activity_at=now - timedelta(days=self.rng.randint(0, 120)),
                )
            )
        Contract.objects.bulk_create(contracts)

        parties = [
            ContractParty(
                cooperative=cooperative,
                contract=contract,
                debtor=self.rng.choice(guarantors),
                role=ContractParty.Role.GUARANTOR,
            )
            for contract in contracts
            if self.rng.random() < 0.25
        ]
        ContractParty.objects.bulk_create(parties, ignore_conflicts=True)
        return len(contracts)
