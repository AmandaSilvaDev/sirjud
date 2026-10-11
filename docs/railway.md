# Railway — configuração passo a passo

Projeto no Railway Pro, ligado ao repositório `AmandaSilvaDev/sirjud`.
Dois ambientes: `production` (só a `main`) e `staging` (base dos PR Environments).

## 1. Criar os serviços (uma vez por ambiente)

1. **Postgres**: *New → Database → PostgreSQL* (versão 16).
2. **web**: *New → GitHub Repo → sirjud*.
   - *Settings → Config-as-code → Railway config file*: `/railway/web.toml`
     (define Dockerfile, pre-deploy `python manage.py predeploy` e healthcheck `/healthz`).
   - *Settings → Networking → Generate Domain* (domínio público `*.up.railway.app`).
   - *Settings → Resources*: 0,5 vCPU / 1 GB.
   - Em **production**: *Settings → Source → Branch* = `main` e ligar **Wait for CI**
     (só faz deploy depois que o GitHub Actions passar).

## 2. Variáveis do serviço `web`

Gere as chaves na sua máquina (valores diferentes para cada ambiente):

```bash
uv run python manage.py generate_keys
```

| Variável | staging | production |
|---|---|---|
| `DJANGO_ENV` | `staging` | `production` |
| `DJANGO_SECRET_KEY` | gerada | gerada (outra) |
| `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` | `${{Postgres.DATABASE_URL}}` |
| `ALLOWED_HOSTS` | `${{RAILWAY_PUBLIC_DOMAIN}}` | domínio público (e o próprio, quando existir) |
| `CSRF_TRUSTED_ORIGINS` | `https://${{RAILWAY_PUBLIC_DOMAIN}}` | `https://<domínio>` |
| `SITE_URL` | `https://${{RAILWAY_PUBLIC_DOMAIN}}` | `https://<domínio>` |
| `FIELD_ENCRYPTION_KEYS` | gerada | gerada (outra) — **guarde cópia fora do Railway** |
| `SEARCH_HMAC_KEY` | gerada | gerada (outra) |
| `WEB_CONCURRENCY` | `2` | `2` |

`PORT` é fornecida pelo Railway. `DJANGO_SETTINGS_MODULE` já vem da imagem
(`config.settings.prod`).

> Perder `FIELD_ENCRYPTION_KEYS` significa perder os CPFs/CNPJs cifrados.
> Guarde a chave de produção num cofre de senhas, fora do Railway.

## 3. Desligar o acesso público ao banco (SEG-21)

1. Abra o serviço **Postgres → Settings → Networking**.
2. Em **Public Networking**, remova o **TCP Proxy** (ícone de lixeira ao lado do
   domínio `*.proxy.rlwy.net`).
3. Confira no serviço `web` que a variável resolvida de `DATABASE_URL` aponta para
   `postgres.railway.internal` (rede privada) — nunca para `proxy.rlwy.net`.
4. Teste: `/healthz` deve continuar respondendo `{"status": "ok", "database": "ok"}`.

Quando precisar acessar o banco manualmente (manutenção), religue o TCP Proxy,
faça o que precisa e **remova de novo** ao terminar. A alteração fica no
histórico do projeto no Railway.

## 4. PR Environments (staging por PR)

*Project Settings → Environments → PR Environments*: ligar, com `staging` como
ambiente base. Cada PR ganha um ambiente temporário com seu próprio Postgres;
o pre-deploy roda `migrate` e `seed_demo --if-empty` (dados fictícios). O
ambiente é apagado quando o PR fecha.

No ambiente `staging`, ligue *Serverless* no serviço `web` para ele dormir sem
tráfego (economia). Não ligue em produção.

## 5. Conferir o deploy

- Log do pre-deploy mostra as migrations e, no staging,
  `Criados: 1 cooperativa, 5 agências, 2 escritórios, 200 contratos.`
- `https://<domínio>/healthz` → `{"status": "ok", "database": "ok"}`.
- `https://<domínio>/` mostra a faixa "Ambiente de testes" (só no staging).

## Serviços Cron (fases seguintes)

Mesma imagem, outro arquivo de config em `railway/` com `startCommand` e
`cronSchedule` (em UTC; Porto Velho = UTC−4). Entram nas fases 4, 5 e 7.
