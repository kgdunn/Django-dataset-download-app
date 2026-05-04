# syntax=docker/dockerfile:1.7

# ---- builder ------------------------------------------------------------
FROM python:3.11-slim AS builder

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
FROM python:3.11-slim AS runtime

RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 \
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

CMD ["gunicorn", "openmv.wsgi:application", "--bind", "0.0.0.0:8000"]
