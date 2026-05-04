"""
Shared Django settings for the openmv project.

`dev.py` and `prod.py` import from here and add the per-environment
DEBUG / DATABASES / ALLOWED_HOSTS / proxy-header bits. Pick which one
to use via DJANGO_SETTINGS_MODULE (defaults to openmv.settings.dev).

See https://docs.djangoproject.com/en/stable/topics/settings/ for an overview
and https://docs.djangoproject.com/en/stable/ref/settings/ for the full list.
"""

import os
from pathlib import Path
from typing import Any

from dotenv import dotenv_values

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Read configuration from process environment first, then fall back to a `.env`
# file if present. This lets containers / CI inject config directly without
# needing to write a `.env`, while keeping the file-based workflow for local dev.
_dotenv_path = BASE_DIR / ".env"
_dotenv = dotenv_values(dotenv_path=_dotenv_path) if _dotenv_path.exists() else {}


def env(key: str, default: str | None = None) -> str | None:
    """Read a config value from os.environ, falling back to .env, then default."""
    value = os.environ.get(key)
    if value is not None:
        return value
    value = _dotenv.get(key)
    if value is not None:
        return value
    return default


def env_list(key: str, default: str) -> list[str]:
    """Read a comma-separated env value as a list of stripped, non-empty entries."""
    raw = env(key, default) or ""
    return [item.strip() for item in raw.split(",") if item.strip()]


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")
assert SECRET_KEY, "SECRET_KEY must be set via environment variable or .env file"

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "datasetapp",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "openmv.middleware.SecurityHeadersMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "openmv.urls"

# `OPTIONS.debug` is set per-environment in dev.py / prod.py, after this
# import, so the template debug toolbar tracks the real DEBUG flag.
TEMPLATES: list[dict[str, Any]] = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "debug": False,
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


WSGI_APPLICATION = "openmv.wsgi.application"


# Password validation
# https://docs.djangoproject.com/en/stable/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/stable/topics/i18n/

LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/stable/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / STATIC_URL.strip("/")

# Media files (admin-uploaded dataset CSV/XLS/XML/MAT files).
# In production Caddy serves /media/ directly; locally `runserver` only
# serves it when openmv/urls.py wires up `static()` under DEBUG.
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Default primary key field type
# https://docs.djangoproject.com/en/stable/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# Upload limits. Datasets uploaded through the admin are tiny (a few hundred
# KB at most); anything larger is almost certainly an accident or abuse.
# Capping these prevents a single oversized multipart from OOM-ing a worker.
DATA_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5 MiB
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024  # 5 MiB
FILE_UPLOAD_PERMISSIONS = 0o644


# Logging
# https://docs.djangoproject.com/en/stable/topics/logging/
#
# Console-only by design: in dev the lines stream to the `runserver` terminal,
# and in prod gunicorn-under-Docker captures stdout/stderr so `docker logs`
# (and any host log shipper) sees them. Override the `datasetapp` log level
# via `DATASETAPP_LOG_LEVEL` for occasional debug runs.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        },
    },
    "loggers": {
        "datasetapp": {
            "handlers": ["console"],
            "level": env("DATASETAPP_LOG_LEVEL", "INFO"),
            "propagate": False,
        },
    },
}
