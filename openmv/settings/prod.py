"""Production settings: Postgres + DEBUG=False + Caddy/Cloudflare proxy headers."""

from .base import *  # noqa: F401,F403
from .base import env, env_list

DEBUG = False

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", ".openmv.net,127.0.0.1")

# Caddy terminates TLS on the host and proxies plain HTTP to gunicorn.
# This header tells Django the request was originally HTTPS.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Required by Django 4.x for any non-GET request (e.g. admin login) when the
# request reaches Django over HTTPS via a reverse proxy.
CSRF_TRUSTED_ORIGINS = [
    "https://openmv.net",
    "https://www.openmv.net",
    "https://test.openmv.net",
]

_db_keys = ["POSTGRES_DB", "POSTGRES_USER", "POSTGRES_PASSWORD", "SQL_HOST", "SQL_PORT"]
_db_settings = {}
for _key in _db_keys:
    _value = env(_key)
    assert (
        _value is not None
    ), f"{_key} must be set via environment variable or .env file"
    _db_settings[_key] = _value

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _db_settings["POSTGRES_DB"],
        "USER": _db_settings["POSTGRES_USER"],
        "PASSWORD": _db_settings["POSTGRES_PASSWORD"],
        "HOST": _db_settings["SQL_HOST"],
        "PORT": _db_settings["SQL_PORT"],
    }
}
