# Progresso

## Fase 0 — Fundação e deploy · branch `fase-0-fundacao`

Status: **pronta para revisão** (11/10/2026). Plano aprovado com todas as
recomendações (D-01 a D-37); veja `docs/PLANO.md`.

### O que mudou

- Projeto Django 5.2 (5.2.17) com `uv` e Python 3.12. O `uv.lock` só aceita
  versões publicadas até 27/09/2026 (`exclude-newer`), contra pacotes
  recém-comprometidos.
- Settings por ambiente (`config/settings/base|dev|test|prod.py`) com
  django-environ. Staging e produção usam `prod.py`; a diferença vem das
  variáveis (`DJANGO_ENV`).
- Segurança já ligada: HTTPS obrigatório, HSTS de 1 ano, CSP fechada
  (`default-src 'self'`, sem inline e sem CDN), X-Frame-Options DENY,
  cookies `__Host-` Secure/HttpOnly/SameSite, senha com no mínimo 12 caracteres.
  `manage.py check --deploy` passa sem avisos. O único aviso silenciado é o de
  preload do HSTS, a decidir quando houver domínio próprio (D-29).
- `/healthz`: faz `SELECT 1` e responde 200 ou 503, sem cache, fora do
  redirecionamento para HTTPS.
- Dockerfile multi-stage: Tailwind standalone v4.3.3 com checksum conferido →
  dependências com uv 0.12.19 → runtime slim com usuário sem privilégios.
  `collectstatic` roda no build; gunicorn escuta em `[::]:$PORT`.
- `railway/web.toml`: Dockerfile, pre-deploy `python manage.py predeploy`
  (`migrate` e, só no staging, `seed_demo --if-empty`) e healthcheck.
- GitHub Actions (`.github/workflows/ci.yml`): ruff (lint e formato), pytest com
  Postgres 16 e cobertura, `makemigrations --check`, bandit (média/alta),
  pip-audit (dependências de produção), gitleaks e `check --deploy`.
- `seed_demo` (Faker pt_BR): 1 cooperativa, 5 agências em RO, 6 produtos,
  2 escritórios (A: ajuizamento e passivo; B: cobrança), 200 contratos com
  devedores e avalistas, distribuídos por situação. É bloqueado em produção.
- Identidade visual: tokens das telas em `static/src/input.css` (`@theme`);
  fontes Montagu Slab e Lato servidas pelo próprio app (licença OFL, D-32);
  logos em `static/img/`. A página inicial provisória segue a tela de login
  (vira o login de fato na Fase 1).
- Documentação: `docs/railway.md` (passo a passo, inclusive como desligar o
  acesso público ao banco), `docs/glossario.md`, `docs/PLANO.md`.

### Adiantado de outras fases (e por quê)

O `seed_demo` da Fase 0 precisa criar cooperativa, escritórios e contratos, e
esses modelos só estavam previstos para as fases 1 e 3. Por isso entraram agora,
na forma mínima:

| Modelo | App | Observação |
|---|---|---|
| `User` (login por e-mail) | accounts | precisa existir na primeira migration; trocar `AUTH_USER_MODEL` depois é muito caro. allauth e MFA entram na Fase 1 |
| `Cooperative`, `Branch`, `LawFirm` | tenants | `Membership`, `Engagement`, tribunais e feriados ficam na Fase 1 |
| `Product`, `Debtor`, `Contract`, `ContractParty` | portfolio | garantias, importação, `RecoveryEntry` e tela ficam na Fase 3 |
| Criptografia AES-256-GCM + HMAC | core | o seed grava CPF/CNPJ, que não pode ficar em texto puro nem no staging |

O validador de CNPJ já aceita o **CNPJ alfanumérico** da Receita (em vigor
desde julho de 2026), além do numérico. Também já existe o validador de número
CNJ (módulo 97), que será usado na Fase 5.

### Como testar no staging

1. Siga `docs/railway.md` (serviços, variáveis, PR Environments).
2. Abra o PR: o Railway cria o ambiente do PR e roda o pre-deploy.
3. No log do pre-deploy: `Criados: 1 cooperativa, 5 agências, 2 escritórios, 200 contratos.`
4. `https://<domínio-do-pr>/healthz` → `{"status": "ok", "database": "ok"}`.
5. `https://<domínio-do-pr>/` → página com a faixa "Ambiente de testes".

### Como rodar localmente

```bash
uv sync                                  # instala dependências (.venv)
cp .env.example .env                     # preencha com: uv run python manage.py generate_keys
docker compose up -d db                  # Postgres 16 local
uv run python manage.py migrate
uv run python manage.py seed_demo
# CSS: baixe o Tailwind standalone v4.3.3 para bin/ (veja o Dockerfile) e rode:
./bin/tailwindcss -i static/src/input.css -o static/css/app.css --watch
uv run python manage.py runserver
uv run pytest
```

### Variáveis novas no Railway

`DJANGO_ENV`, `DJANGO_SECRET_KEY`, `DATABASE_URL`, `ALLOWED_HOSTS`,
`CSRF_TRUSTED_ORIGINS`, `SITE_URL`, `FIELD_ENCRYPTION_KEYS`, `SEARCH_HMAC_KEY`,
`WEB_CONCURRENCY` (opcional). Valores sugeridos em `docs/railway.md`.

### Verificação local feita

- `pytest`: 41 testes passando, cobertura de 87% (Postgres 16).
- `ruff check` e `ruff format --check`: sem problemas.
- `bandit -ll`: sem achados. `pip-audit --strict`: nenhuma vulnerabilidade conhecida.
- `check --deploy --fail-level WARNING` com as settings de produção: sem problemas.
- Build do Tailwind e servidor local: `/healthz`, página inicial, CSS e fontes
  respondem 200; layout conferido em 1440 px e 500 px.
- **Não testado localmente:** o build da imagem Docker. O Docker Desktop desta
  máquina travou junto com o WSL durante a sessão; os testes rodaram num
  Postgres 16 portátil. O build da imagem é validado pelo Railway no deploy do PR.

### Pendências

- Configurar o Railway conforme `docs/railway.md` (precisa do seu acesso).
- Ligar a proteção da `main` no GitHub: exigir PR e CI verde antes do merge.
- Instalar o `uv` na sua máquina (`winget install astral-sh.uv`) e o GitHub CLI
  (`winget install GitHub.cli`), se quiser abrir PRs pelo terminal.
- Respostas que ainda dependem de você: domínio no Cloudflare (D-29), prazos
  de prescrição por tipo de ação (D-09) e uma planilha de exemplo da
  cooperativa piloto (D-10).
