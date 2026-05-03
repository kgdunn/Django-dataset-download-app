"""
Shared Django settings for the openmv project.

`dev.py` and `prod.py` import from here and add the per-environment
DEBUG / DATABASES / ALLOWED_HOSTS / proxy-header bits. Pick which one
to use via DJANGO_SETTINGS_MODULE (defaults to openmv.settings.dev).

See https://docs.djangoproject.com/en/stable/topics/settings/ for an overview
and https://docs.djangoproject.com/en/stable/ref/settings/ for the full list.
"""

from pathlib import Path
from typing import Any

from dotenv import dotenv_values

BASE_DIR = Path(__file__).resolve().parent.parent.parent

dotenv_file = BASE_DIR / ".env"
assert Path(dotenv_file).parent.exists(), f"{dotenv_file} directory does not exist"
assert Path(dotenv_file).exists(), f"{dotenv_file} does not exist"

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = dotenv_values(dotenv_path=dotenv_file).get("SECRET_KEY", None)
assert SECRET_KEY is not None

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
