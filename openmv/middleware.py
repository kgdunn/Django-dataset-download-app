"""Project-local middleware.

`SecurityHeadersMiddleware` adds the browser-side defence-in-depth headers
that Django's `SecurityMiddleware` does not set:

* ``Content-Security-Policy`` — neutralises injected `<script>` (the
  `bleach`-based ``sanitise_markup`` filter is the primary defence;
  the CSP is the second line for any future template that forgets it).
* ``Permissions-Policy`` — opt out of legacy interest-cohort and the
  device-sensor APIs we don't need.
* ``Cross-Origin-Opener-Policy`` — isolate browsing-context groups.

CSP currently allows ``'unsafe-inline'`` for both `script-src` and
`style-src` because base.html's theme-toggle script and dataset_info.html's
ECharts setup are inlined, and base.html's styles are an inline `<style>`
block. Externalising those is tracked as a follow-up.
"""

CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src 'self' https://fonts.gstatic.com; "
    "img-src 'self' data:; "
    "connect-src 'self'; "
    "frame-ancestors 'none'; "
    "base-uri 'self'; "
    "form-action 'self'"
)

PERMISSIONS_POLICY = "interest-cohort=(), camera=(), microphone=(), geolocation=()"


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault("Content-Security-Policy", CSP)
        response.setdefault("Permissions-Policy", PERMISSIONS_POLICY)
        response.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        return response
