# Security

This is the canonical security record for the openmv.net Django site.
It captures what's been audited, what's been fixed, and what's deferred,
so future maintainers don't have to spelunk PR descriptions to know
what state the site is in.

## Reporting a vulnerability

Please email Kevin Dunn — the maintainer's address is on
<https://learnche.org>. Do **not** open a public GitHub issue for
suspected vulnerabilities; we'll create one once we've assessed the
report and have a fix in flight.

GitHub's "Security" tab on the repo points reporters here via a
top-level `SECURITY.md` redirect.

---

## Audit findings (2026-05-04)

A full code review of the application, settings, deployment, and
supply-chain surface. Severity reflects the realistic worst case for
*this* site (small read-only public catalogue with one admin), not a
generic CVSS score.

| # | Severity | File:line                                                | Issue                                                                                                                                                                                            | Status                  |
|---|----------|----------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------|
| 1 | Critical | `datasetapp/templates/datasetapp/dataset_info.html:4,13,14` | Stored XSS via `\|safe` on admin-authored `name` / `description` / `data_source`. Compromised admin or future co-maintainer can inject `<script>` that fires for every visitor.                  | **Fixed in v1.5.0** — `\|sanitise_markup` (bleach allowlist) for the two text fields; auto-escape for the title. **Follow-up in v1.6.3:** `<img>` re-permitted in the allowlist (`src` / `alt` / `title` / `width` / `height` only) so legacy dataset figures render again; event-handler attributes and `javascript:` URLs remain stripped. |
| 2 | High     | `datasetapp/templates/datasetapp/all_datasets.html:15`   | Contradictory `\|safe\|escape` filter chain on `special_message`. Not exploitable today (hardcoded view string) but invites future misuse.                                                       | **Fixed in v1.5.0** — markup inlined in template, context variable removed from `display_all`. |
| 3 | High     | `datasetapp/views.py:179-180`                            | `[base, ext] = file_name.split(".")` raises `ValueError → 500` on any input without exactly one dot (`/file/foo`, `/file/foo.bar.csv`). Easy log-flood / cheap DoS.                              | **Fixed in v1.5.0** — strict regex pre-check, `rsplit(".", 1)`. |
| 4 | High     | `datasetapp/views.py:67-89` (`_csv_preview`)             | `csv.Sniffer().sniff(...)` reachable from any visitor on `/info/<slug>` and prone to catastrophic backtracking on adversarial CSVs uploaded by admin.                                            | **Fixed in v1.5.0** — Sniffer removed, `csv.excel` dialect used unconditionally. |
| 5 | Medium   | `datasetapp/models.py:114-115` (`DataFile.link_to_file`) | No extension or MIME validation on uploads. Admin can upload `.html` masquerading as `.csv`, served by Caddy with the wrong type.                                                                | **Fixed in v1.5.0** — `FileExtensionValidator` + `DataFile.clean()` enforces declared `file_type` matches actual extension. |
| 6 | Medium   | `openmv/settings/prod.py`                                | Missing explicit `SESSION_COOKIE_HTTPONLY` / `SESSION_COOKIE_SAMESITE` / `CSRF_COOKIE_HTTPONLY` / `CSRF_COOKIE_SAMESITE` and no `Content-Security-Policy` / `Permissions-Policy` headers.       | **Fixed in v1.5.0** — four cookie flags set explicitly; `openmv.middleware.SecurityHeadersMiddleware` emits CSP, Permissions-Policy, COOP. |
| 7 | Medium   | `openmv/settings/base.py`                                | No `DATA_UPLOAD_MAX_MEMORY_SIZE` / `FILE_UPLOAD_MAX_MEMORY_SIZE` / `FILE_UPLOAD_PERMISSIONS` overrides — relies on Django defaults.                                                              | **Fixed in v1.5.0** — capped at 5 MiB; uploads written `0o644`. |
| 8 | Medium   | `datasetapp/admin.py:7,19,28`                            | `list_per_page = 2000` on all three admins; `Hit` table is editable in admin even though it's a write-once audit log.                                                                            | **Fixed in v1.5.0** — `list_per_page = 100`; `HitAdmin` rows readonly; `date_hierarchy` + `list_filter` for scoped queries. |
| 9 | Medium   | `datasetapp/views.py:92-109` (`_download_series`)        | 365-day per-dataset aggregation recomputed on every detail-page view. Cheap today; future-DoS as `Hit` grows.                                                                                    | **Fixed in v1.5.0** — cached for 1 h via `django.core.cache`. See Issue F for the structural follow-up. |
| 10 | Low     | `datasetapp/templates/datasetapp/base.html:21`, `dataset_info.html:153` | MathJax + ECharts loaded from CDN with floating `mathjax@2` / `echarts@5` tags and no SRI. CDN compromise = stored XSS.                                                                          | **Fixed in v1.6.2** — version pins (`mathjax@2.7.9` / `echarts@5.5.1`) + `crossorigin="anonymous"` from v1.5.0, and `integrity="sha384-…"` hashes added in v1.6.2 (Issue K). Vendoring (Issue D / #72) is still the cleaner end-state. |
| 11 | Low     | `.github/workflows/ci.yml`                               | No `permissions:` block; `actions/checkout@v4` and `astral-sh/setup-uv@v6` referenced by floating tag. (`deploy.yml` is already fine.)                                                           | **Partially fixed in v1.5.0** — `permissions: contents: read` added; `pip-audit` step added. SHA-pinning of the two third-party actions deferred (see Issue J). |
| 12 | Low     | `Dockerfile:6`                                           | `COPY --from=ghcr.io/astral-sh/uv:latest` — floating tag.                                                                                                                                        | **Fixed in v1.5.0** — pinned to `ghcr.io/astral-sh/uv:0.8.17`. |
| 13 | Info    | `pyproject.toml`                                         | `psycopg2-binary`, `python-dotenv`, `gunicorn` had no lower bounds; `pip-audit` not in dev group.                                                                                                | **Fixed in v1.5.0** — lower bounds added; `pip-audit` in dev group + non-blocking CI step. |

### Already-correct findings (no change needed)

- ORM-only DB access — no `.raw()` / `.extra()` / cursor strings; SQL injection surface is zero.
- All views are GET-only — no CSRF surface today.
- `SECRET_KEY` is asserted in `base.py` — fails loudly if missing.
- `CSRF_TRUSTED_ORIGINS` correctly scoped to the three real hostnames; no wildcards.
- `SECURE_PROXY_SSL_HEADER` correctly trusts only the Caddy-stripped `X-Forwarded-Proto`.
- `docker-compose.prod.yml` binds both services to `127.0.0.1` only; Caddy is the sole public process.
- `DEBUG = False` in prod (and CI); SQLite is dev-only.
- `DatasetManager.get_queryset` filters `is_hidden=True` from both the public site and the admin list.
- The deploy SSH key is restricted to a forced command, so a leaked key can only re-trigger the deploy script.
- `.dockerignore` excludes `.env`, `.git`, `__pycache__`, etc.
- The legacy `media/`-prefix migration on `DataFile.link_to_file` already happened during the Hetzner cutover.

---

## Host-side recommendations (not enforceable from this repo)

These don't ship in the repo but should be applied on the Hetzner host
or in Cloudflare. Each one is also tracked as a "follow-up issue" below.

### Caddy: rate-limit `/admin/login/`

The host-installed Caddy needs the `caddy-ratelimit` module
(<https://github.com/mholt/caddy-ratelimit>). Add to `/etc/caddy/Caddyfile`
in the openmv site block:

```
@admin path /admin/*
rate_limit @admin {
    zone admin_login {
        key {http.request.remote.host}
        events 5
        window 1m
    }
}
```

After editing: `sudo caddy validate --config /etc/caddy/Caddyfile && sudo systemctl reload caddy`.

### Cloudflare: WAF rule on `/admin/*`

In the Cloudflare dashboard for `openmv.net`:

1. **Security → WAF → Custom rules** → "Create rule":
   - Field: `URI Path`, Operator: `starts with`, Value: `/admin/`
   - Action: `Managed Challenge`
2. **Security → Bots** → enable "Bot Fight Mode" (free tier is sufficient).
3. **Caching → Page Rules** → "URL: `*openmv.net/admin/*`" → Cache Level: Bypass.

`test.openmv.net` is DNS-only (grey cloud) so these rules don't apply
there — Caddy is the only filter for staging. Because `test.openmv.net`
bypasses Cloudflare's edge, Caddy must serve a publicly-trusted cert on
that hostname directly; the Cloudflare Origin Certificate used for
`openmv.net` / `www.openmv.net` is signed by Cloudflare's internal CA
and is only trusted when consumed by Cloudflare. See
[`docs/caddy.md`](caddy.md) for the canonical site-block split that
keeps `test.openmv.net` on Let's Encrypt (issue #89).

#### Bot Fight Mode and dataset downloads

Bot Fight Mode flags non-browser User-Agents (`Python-urllib/3.X`,
`python-requests/...`, etc.) and can return 403 to legitimate Python
clients hitting dataset URLs (issue #86). Until v1.6.4 the public
download path also redirected through `/media/datasets/...`, so a
single `pandas.read_csv("https://openmv.net/file/<slug>.csv")` was
evaluated by Cloudflare twice on two different paths. Since v1.6.4
the `/file/*` view streams the bytes directly via `FileResponse`, so
only `/file/*` is in the path of legitimate Python downloads. If Bot
Fight Mode starts blocking that surface too, add a Custom Rule with
**Field**: `URI Path`, **Operator**: `starts with`, **Value**:
`/file/`, **Action**: `Skip` → "All remaining custom rules" + "Bot
Fight Mode".

### fail2ban jail (alternative to caddy-ratelimit)

`/etc/fail2ban/filter.d/caddy-admin.conf`:

```
[Definition]
failregex = ^.*"GET /admin/login/.*" 4[0-9][0-9].*"<HOST>".*$
            ^.*"POST /admin/login/.*" 4[0-9][0-9].*"<HOST>".*$
```

`/etc/fail2ban/jail.d/caddy-admin.conf`:

```
[caddy-admin]
enabled  = true
port     = http,https
logpath  = /var/log/caddy/access.log
maxretry = 5
findtime = 600
bantime  = 3600
```

### HSTS preload

`prod.py` keeps `SECURE_HSTS_SECONDS = 300` and
`SECURE_HSTS_PRELOAD = False` as a staged rollout. Once a week of
production traffic confirms `X-Forwarded-Proto: https` is being honoured
(no SSL-redirect loops), bump via `.env`:

```
SECURE_HSTS_SECONDS=31536000
```

…and edit `prod.py` to flip `SECURE_HSTS_PRELOAD = True` in a separate
PATCH release. Then submit `openmv.net` to <https://hstspreload.org/>.

---

## Issues to file

The plan that produced v1.5.0 deferred these items. They should each
become a GitHub issue on `kgdunn/Django-dataset-download-app`.
Cross-reference them from this document so the audit trail stays
attached to the audit, not to a transient PR description.

### Issue A — Restrict `/admin/` access by IP allowlist or VPN
- **Severity:** Medium (defence-in-depth).
- **Why:** Bruteforce against `/admin/login/` from the open internet eventually finds a weak password. The Cloudflare and Caddy rate-limits above are mitigation; an IP allowlist is prevention.
- **Proposed fix:** Either Caddy `@admin` matcher with an IP allowlist (maintainer's residential static + Tailscale CIDRs only), or a Cloudflare Access policy on `/admin/*`.

### Issue B — Add `django-axes` for admin login throttling
- **Severity:** Medium.
- **Why:** Defence in depth alongside Issues A and the Caddy/Cloudflare rate-limits.
- **Proposed fix:** `uv add django-axes`, register in `INSTALLED_APPS` + `MIDDLEWARE`, lock account 30 min after 5 failures, log lockouts via the existing `datasetapp` logger.

### Issue C — Enforce 2FA on admin accounts
- **Severity:** Medium.
- **Why:** Admin compromise is the highest-impact credential incident for this site (XSS to all visitors, data tampering, file deletion). Even bleach-sanitised descriptions wouldn't survive an attacker who could swap a `DataFile.link_to_file` for a hostile URL.
- **Proposed fix:** `django-otp` + `django-two-factor-auth`, mandatory for `is_staff=True`. Behaviour change — needs a maintainer rollout window.

### Issue D — Vendor the CDN scripts (MathJax, ECharts) as static assets
- **Severity:** Low (defence-in-depth, but obviates Issue E and finding 10's residual risk).
- **Why:** Even with SRI, a `script-src` allow-list that includes `cdn.jsdelivr.net` is broader than necessary. Vendoring lets us tighten to `'self'` only.
- **Proposed fix:** `npm install --save-dev` the two libs at pinned versions (or commit the CDN files directly under `staticfiles/vendor/`), serve via `STATIC_URL`, drop the `cdn.jsdelivr.net` allowance from CSP.

### Issue E — Eliminate inline `<script>` and `<style>` blocks so CSP can drop `'unsafe-inline'`
- **Severity:** Low.
- **Why:** Today's CSP keeps `'unsafe-inline'` for both `script-src` and `style-src` because `base.html`'s theme-toggle script and large inline `<style>`, plus `dataset_info.html`'s ECharts setup and copy-button script, are all inlined. Stricter CSP would block any reflected-XSS even before bleach runs.
- **Proposed fix:** Move the inline blocks into `static/openmv.css` / `static/openmv.js` and tighten the CSP. Test interaction with the dark-mode FOUC mitigation in `base.html:7-16` (the early `localStorage` read is what the inline script is for).

### Issue F — Pre-aggregate `Hit` rows into a daily-counts table
- **Severity:** Info (future-DoS).
- **Why:** `_download_series` walks every `Hit` row in the last 365 days. The 1 h cache added in v1.5.0 papers over it, but the cache miss still has to scan everything; once `Hit` is millions of rows that's a multi-second query.
- **Proposed fix:** New `HitDaily(date, dataset, count)` table updated by a nightly management command (or by a post-save signal that does an upsert on `(date, dataset)`). Read from that table in `_download_series`. Keep the raw `Hit` table for fine-grained queries.

### Issue G — Replace the `description` / `data_source` admin widget with a markup-aware editor
- **Severity:** Info.
- **Why:** Admins type raw HTML today, which `bleach` then sanitises at render. A WYSIWYG (or a Markdown widget) would let authors stop hand-writing tags and would naturally constrain the input to what `bleach` allows.
- **Proposed fix:** Either `django-markdownx` + render markdown to HTML (then still pass through bleach), or a small custom `forms.Textarea` widget with `help_text` linking to the allowed-tags list.

### Issue H — Pin Docker base images by digest
- **Severity:** Low (supply chain).
- **Why:** `python:3.11-slim` and `postgres:16-alpine` are pinned only by minor version. v1.5.0 pinned the `uv` image, but the two main bases remain floating.
- **Proposed fix:** Pin both to `…@sha256:…` digests in `Dockerfile` and `docker-compose.prod.yml`. Add a Renovate / Dependabot config to bump them on a schedule.

### Issue I — Add a Dockerfile `HEALTHCHECK`
- **Severity:** Low.
- **Why:** Caddy currently has no signal whether gunicorn is unhealthy mid-request beyond its own connect-failure detection.
- **Proposed fix:** Add a lightweight `/healthz` view (returns `200 OK` with cache disabled and never touches the DB) and a `HEALTHCHECK CMD curl -fsS http://127.0.0.1:8000/healthz` in the runtime stage.
- **Status:** **Fixed in v1.6.1** — `datasetapp.views.healthz` (decorated with `@never_cache`, no DB / template / auth) wired at `/healthz`; `Dockerfile` runtime stage installs `curl` and runs `HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3 CMD curl -fsS http://127.0.0.1:8000/healthz`. Container flips to `(unhealthy)` within ~90 s of gunicorn going dark.

### Issue J — Pin GitHub Actions to full commit SHAs
- **Severity:** Low (supply chain).
- **Why:** v1.5.0 added `permissions: contents: read` and a `pip-audit` step but `actions/checkout@v4` and `astral-sh/setup-uv@v6` are still floating tags that the action owner can re-point. Full SHAs are immutable.
- **Proposed fix:** Look up the latest releases of both actions, pin to their commit SHAs with a `# vX.Y.Z` comment, and add a `.github/dependabot.yml` for `package-ecosystem: github-actions` so Dependabot bumps the SHAs automatically.

### Issue K — Generate and inline SRI hashes for the two CDN `<script>` tags
- **Severity:** Low.
- **Status:** **Fixed in v1.6.2.**
- **What landed:** `make sri` (added in v1.5.0) was run; the two `integrity="sha384-…"` values are inlined on the ECharts `<script>` in `base.html` and the MathJax `<script>` in `dataset_info.html`. The TODO comment blocks above each tag were updated accordingly. A tampered or substituted CDN response is now refused by the browser.
- **Note:** Vendoring (Issue D / #72) would let us drop `cdn.jsdelivr.net` from the CSP `script-src` allow-list entirely and obviate SRI; until that lands, version pin + `crossorigin="anonymous"` + SRI is the layered defence.

### Explicitly accepted (not filed)

- `data/` and `media/` are bind-mounted into the container as RW. Read-only is impractical because the app writes uploads. Risk accepted; container UID 1000 ≠ host root limits the blast radius.
- The `special_message` `|safe|escape` template gotcha (CLAUDE.md) is removed entirely by v1.5.0 — the template inlines the literal markup. No follow-up needed.

---

## Where to look in the code

| Concern                          | File                                                       |
|----------------------------------|------------------------------------------------------------|
| HTML sanitisation (bleach)       | `datasetapp/templatetags/extra_tags.py`                    |
| Filename validation              | `datasetapp/views.py` (`_DOWNLOAD_FILENAME_RE`, `download_dataset`) |
| CSV preview safety               | `datasetapp/views.py` (`_csv_preview`)                     |
| Upload validation                | `datasetapp/models.py` (`DataFile.clean`)                  |
| Admin write-once policy          | `datasetapp/admin.py` (`HitAdmin.readonly_fields`)         |
| Security headers                 | `openmv/middleware.py`                                     |
| Cookie + transport flags         | `openmv/settings/prod.py`                                  |
| Upload size limits               | `openmv/settings/base.py`                                  |
| Regression tests                 | `datasetapp/tests/test_security.py`                        |
