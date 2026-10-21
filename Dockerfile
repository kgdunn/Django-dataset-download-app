# syntax=docker/dockerfile:1.7

# ---- builder ------------------------------------------------------------
# Pinned by digest so two builds five minutes apart can't end up on different
# python:3.11-slim contents. Dependabot (`docker` ecosystem in
# .github/dependabot.yml) opens weekly bump PRs; CI catches breakage before
# merge. Bump in lockstep with the runtime stage below — the multi-stage
# build expects identical glibc / libpq versions in both.
FROM python:3.14-slim@sha256:ce40764625a4ff50df3548277632e7f96c4e77fe75fa848aae9885476e7df5a4 AS builder

# Pinned to a specific uv version so a malicious push to ghcr.io/astral-sh/uv
# can't land in our build. Bump in lockstep with `uv self update`.
COPY --from=ghcr.io/astral-sh/uv:0.8.17 /uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# ---- runtime ------------------------------------------------------------
FROM python:3.14-slim@sha256:ce40764625a4ff50df3548277632e7f96c4e77fe75fa848aae9885476e7df5a4 AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 curl \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 app

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --chown=app:app . .

# WORKDIR created /app as root-owned. The COPY --chown above sets ownership
# on the copied contents, but not on /app itself. Make the working directory
# writable by the runtime user so the app can create files like logfile.log
# (datasetapp/views.py opens this at import time via RotatingFileHandler).
RUN chown app:app /app

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

USER app

EXPOSE 8000

# Liveness probe: hits the @never_cache /healthz view in datasetapp/urls.py.
# `-f` so a 5xx still fails the check (curl exits non-zero on HTTP errors only
# when -f is set). 30s × 3 retries ⇒ container flips to (unhealthy) within
# ~90s of gunicorn going dark.
HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/healthz || exit 1

CMD ["gunicorn", "openmv.wsgi:application", "--bind", "0.0.0.0:8000"]
