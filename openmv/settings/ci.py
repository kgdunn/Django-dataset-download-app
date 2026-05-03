"""CI settings: prod-like (Postgres, DEBUG=False) but test-client friendly.

Imports prod, then disables the HTTPS-only middleware behaviour that would
otherwise 301-redirect every Django test client request, since the test
client speaks plain HTTP. Used by .github/workflows/ci.yml so pytest runs
against the same database engine production uses.
"""

from .prod import *  # noqa: F401,F403

SECURE_SSL_REDIRECT = False
SECURE_HSTS_SECONDS = 0
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
