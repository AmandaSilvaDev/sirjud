# SIRJUD COOP — regras do projeto

Sistema Integrado de Recuperação de Crédito Jurídico Cooperativo.
"Inteligência jurídica na recuperação de crédito."

Plataforma onde cooperativas de crédito e escritórios de advocacia terceirizados
trabalham no mesmo fluxo: encaminhamento, cobrança extrajudicial, ajuizamento,
acordos, BNDU e polo passivo. Requisitos completos em `docs/requisitos.md`;
telas de referência em `docs/telas/*.dc.html` (HTML com estilos inline — use como
referência visual de layout, cores e textos; os `src="/_blob/..."` são o
`docs/telas/logo-branco.png` e `docs/telas/logo.png`).

## Stack (não trocar sem perguntar)

- Python 3.12, gerenciado com `uv`
- Django 5.2 LTS (monólito: páginas + API num serviço só)
- PostgreSQL 16 (Railway, rede privada)
- Front: templates Django + HTMX + Alpine.js + Tailwind CSS (CLI standalone no build, sem Node em produção)
- API para BI: Django REST Framework + drf-spectacular (somente leitura)
- Login/MFA: django-allauth (com `allauth.mfa`, TOTP + códigos de recuperação)
- Bloqueio de tentativas: django-axes · CSP: django-csp · rate limit: django-ratelimit
- Arquivos: Cloudflare R2 via django-storages (S3), bucket privado, links temporários
- E-mail: django-anymail + Resend
- PDF: WeasyPrint · Excel: openpyxl · dados falsos: Faker (pt_BR)
- Testes: pytest-django + factory_boy · Qualidade: ruff, bandit, pip-audit, gitleaks
- Servidor: gunicorn + whitenoise · Deploy: Railway (Dockerfile)
- Tarefas agendadas: serviços Cron do Railway rodando `manage.py <comando>` (sem Redis/Celery no MVP)
- Aprovadas depois (D-31): django-environ, psycopg[binary], argon2-cffi, cryptography,
  boto3 (via django-storages), pytest-cov. Chamadas HTTP externas (DataJud, HIBP) com
  `urllib` da biblioteca padrão. Fontes servidas localmente (sem Google Fonts).

## Regras de segurança (inegociáveis)

1. Toda consulta a dados de negócio passa por managers com escopo de tenant
   (cooperativa) e de escritório. Nunca usar `Model.objects` direto em views para
   dados de cliente. Cada recurso novo ganha teste que tenta ler dado de outra
   cooperativa e de outro escritório — e precisa falhar (404).
2. Permissão checada no servidor em toda view e endpoint (perfil × tela × ação:
   consultar, criar, alterar, excluir). Esconder botão não é controle de acesso.
3. Somente ORM/queries parametrizadas. Proibido SQL montado com texto do usuário.
4. MFA obrigatório para todos. Bloqueio após 5 tentativas. Sessão: 30 min de
   inatividade, máximo 8 h. Senhas com Argon2 e mínimo de 12 caracteres.
5. CPF/CNPJ e dados bancários criptografados no banco + coluna HMAC para busca.
   Mascarar CPF em listas e painéis.
6. Log de auditoria imutável (trigger no PostgreSQL bloqueia UPDATE/DELETE na
   tabela). Registrar: login, consulta de processo, criação, alteração (antes e
   depois), exclusão, download, aprovação e toda consulta feita por IA.
7. Segredos só em variáveis de ambiente do Railway. Nunca no código, nunca em
   `.env` versionado. `.env.example` sem valores reais.
8. Headers: HTTPS obrigatório, HSTS, CSP, X-Frame-Options DENY, cookies Secure/HttpOnly/SameSite.
9. Staging nunca usa dados reais. Use `manage.py seed_demo` com Faker.
10. Não adicionar dependências fora da lista sem perguntar.

## Convenções

- Código, modelos e tabelas em inglês; interface 100% em português do Brasil.
  Glossário de domínio em `docs/glossario.md` (manter atualizado).
- Valores monetários em `Decimal` (nunca float); datas com fuso America/Porto_Velho
  (Rondônia, UTC-4), armazenadas em UTC.
- Número CNJ validado (formato NNNNNNN-DD.AAAA.J.TR.OOOO e dígito verificador módulo 97).
- Cada app Django por domínio, dentro do pacote `apps/`: `core` (base comum),
  `accounts`, `tenants`, `audit`, `documents` (arquivos no R2), `portfolio`
  (contratos/devedores), `referrals` (encaminhamentos), `lawsuits` (processos,
  movimentações, comentários), `collections` (cobrança), `notifications`
  (alertas e resumo diário), `dashboards`, `api`. Plano completo em `docs/PLANO.md`.
- Identidade visual: azul #002D62 (70%), verde #198754 (25%), cinza #F0F2F5;
  botões #157347; títulos Montagu Slab, textos Lato. Copie os tokens das telas.

## Fluxo de trabalho

- Nunca fazer push direto na `main` (ela faz deploy em produção no Railway).
  Trabalhar em branch `fase-N-descricao`, abrir PR, CI verde, eu aprovo.
- Ao fim de cada fase: rodar testes, atualizar `docs/PROGRESSO.md` (o que foi
  feito, como testar, pendências) e PARAR para minha validação.
- Em dúvida de regra de negócio, perguntar — não inventar.
- Código gerado por IA é revisado: explique no PR as partes de permissão,
  consultas ao banco e uploads.
