"""Local-development settings: SQLite + DEBUG=True + runserver-friendly hosts."""

from .base import *  # noqa: F401,F403
from .base import BASE_DIR, TEMPLATES, env_list

DEBUG = True

TEMPLATES[0]["OPTIONS"]["debug"] = DEBUG

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "127.0.0.1,localhost")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
