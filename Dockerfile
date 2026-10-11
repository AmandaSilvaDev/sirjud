# syntax=docker/dockerfile:1.7
# Imagem única: serviço web e serviços Cron do Railway (só muda o comando).

ARG PYTHON_IMAGE=python:3.12-slim-bookworm

# 1) CSS: Tailwind standalone (sem Node). Versão e checksum fixos.
FROM debian:bookworm-slim AS css
ARG TAILWIND_VERSION=v4.3.3
ARG TAILWIND_SHA256=dc61b3ac6b8c9ca874c0cc4c57b2409791a64c5540404ca5f5367360babc313a
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*
RUN curl -fsSL -o /usr/local/bin/tailwindcss \
      "https://github.com/tailwindlabs/tailwindcss/releases/download/${TAILWIND_VERSION}/tailwindcss-linux-x64" \
    && echo "${TAILWIND_SHA256}  /usr/local/bin/tailwindcss" | sha256sum -c - \
    && chmod +x /usr/local/bin/tailwindcss
WORKDIR /src
COPY static ./static
COPY templates ./templates
COPY apps ./apps
RUN tailwindcss -i static/src/input.css -o static/css/app.css --minify

# 2) Dependências Python com uv, a partir do uv.lock (sem dependências de desenvolvimento).
FROM ${PYTHON_IMAGE} AS deps
COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/opt/venv
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
# Sem --mount=type=cache: no Railway ele exige o id do serviço no prefixo.
RUN uv sync --frozen --no-dev --no-cache

# 3) Runtime: só o necessário, usuário sem privilégios.
FROM ${PYTHON_IMAGE} AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:${PATH}" \
    DJANGO_SETTINGS_MODULE=config.settings.prod
RUN groupadd --system app && useradd --system --gid app --home /app app
WORKDIR /app
COPY --from=deps /opt/venv /opt/venv
COPY --chown=app:app . .
COPY --from=css --chown=app:app /src/static/css/app.css ./static/css/app.css
# collectstatic roda no build com valores descartáveis (nenhum segredo real na imagem).
RUN DJANGO_SECRET_KEY=build-only DATABASE_URL=postgres://build@localhost/build \
    FIELD_ENCRYPTION_KEYS=build:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA= SEARCH_HMAC_KEY=build-only \
    python manage.py collectstatic --noinput \
    && chown -R app:app /app/staticfiles
USER app
EXPOSE 8000
CMD ["gunicorn", "-c", "config/gunicorn.conf.py", "config.wsgi:application"]
