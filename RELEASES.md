# Releases

## v1.6.3

Bugfix for v1.5.0's bleach allowlist: `<img>` was not on the list, so any
image an admin had embedded in `Dataset.description` or `Dataset.data_source`
disappeared from the detail page after the security-hardening release. The
allowlist now permits `<img>` with a tightly scoped attribute set, so legacy
dataset figures render again without re-opening the XSS hole that finding 1
in `docs/SECURITY.md` closed.

- **`datasetapp/templatetags/extra_tags.py`**: `"img"` added to
  `_ALLOWED_TAGS`; `_ALLOWED_ATTRS["img"]` set to
  `["src", "alt", "title", "width", "height"]`. Event-handler attributes
  (`onerror`, `onload`, …) are not on the list, so bleach drops them; `src`
  values are filtered against `_ALLOWED_PROTOCOLS` (`http`, `https`,
  `mailto`), so `javascript:` URLs are rejected. The CSP `img-src 'self'
  data:` in `openmv/middleware.py` is unchanged — same-origin `/media/...`
  references are what admins use in practice.
- **`datasetapp/tests/test_security.py`**: new
  `test_sanitise_markup_strips_event_handlers_from_img` pins the
  attribute-stripping contract; `test_sanitise_markup_preserves_allowed_tags`
  parametrised with a benign `<img src="/media/datasets/foo.png" alt="…">`
  case; `test_detail_page_does_not_render_admin_supplied_script` updated to
  expect `<img` to survive but `onerror` / `onload` / `javascript:` to be
  stripped (the original assertion that *no* `<img` survived is what locked
  the regression in).
- **`docs/SECURITY.md`**: finding 1's "Fixed in v1.5.0" cell amended with a
  pointer to the v1.6.3 follow-up.

## v1.6.2

Defence-in-depth follow-up to v1.5.0's CDN pinning. Adds Subresource
Integrity (SRI) `sha384` hashes to the two `<script>` tags that load
ECharts and MathJax from `cdn.jsdelivr.net`, so a tampered or substituted
CDN response is refused by the browser. Closes Issue K in
`docs/SECURITY.md` (and the SRI half of finding 10).

- **`datasetapp/templates/datasetapp/base.html`**: ECharts `<script>`
  gets `integrity="sha384-Mx5lkUEQPM1pOJCwFtUICyX45KNojXbkWdYhkKUKsbv391mavbfoAmONbzkgYPzR"`.
  Comment block above the tag is updated — the old "add this once the
  maintainer has network access" TODO is gone, replaced with a one-liner
  pointing readers at `make sri` if the pinned version ever changes.
- **`datasetapp/templates/datasetapp/dataset_info.html`**: MathJax
  `<script>` gets `integrity="sha384-vi9R4hb1goLJPJDHY+dOmXxcY3HGv6tJIwHxy5JunOTxJGHbsSuubPgl++SNxYYi"`.
  The comment notes that the hash is over `MathJax.js`'s bytes and that
  the `?config=TeX-AMS-MML_HTMLorMML` query string is ignored by jsDelivr
  for static files (so SRI still matches).
- **`docs/SECURITY.md`**: Issue K marked **Fixed in v1.6.2**; finding 10
  closed for the CDN-script half. Vendoring (Issue D / #72) remains the
  fuller fix and is still open.
- The `make sri` target in `Makefile` (added in v1.5.0) is unchanged —
  it remains the canonical way to recompute hashes if either CDN script
  is ever bumped to a new patch version.

## v1.6.1

Operational follow-up to v1.5.0's audit. Adds a Docker liveness probe so a
half-broken container (gunicorn workers blocked on a slow query, OOM-killed,
etc.) flips to `(unhealthy)` and `restart: unless-stopped` can recycle it.
Closes Issue I in `docs/SECURITY.md`.

- **`datasetapp/views.py`**: new `healthz(request)` view, decorated with
  `@never_cache`, returning `HttpResponse("ok\n", content_type="text/plain")`.
  No DB, no template, no auth — pure liveness signal.
- **`datasetapp/urls.py`**: wired at `/healthz` (reverse name
  `datasetapp:healthz`). Mounted at the top of the patterns; outside `/admin/`
  so any future Caddy or Cloudflare admin rate-limit doesn't touch it.
- **`Dockerfile`**: runtime stage installs `curl` (alongside `libpq5`) and
  adds `HEALTHCHECK --interval=30s --timeout=3s --start-period=20s --retries=3
  CMD curl -fsS http://127.0.0.1:8000/healthz`. The `-f` flag is required so
  a 5xx still fails the check.
- **`datasetapp/tests/test_views.py`**: three smoke tests pin the contract —
  200 + `ok\n` + `text/plain`, `Cache-Control: no-cache, no-store, max-age=0`
  (proves `@never_cache` is applied), and no `Hit` row written (proves the
  view doesn't accidentally exercise the download codepath).
- **`docs/SECURITY.md`**: Issue I marked **Fixed in v1.6.1**.

## v1.6.0

Sortable columns on the homepage / tag-filter table (issue #81). Click any
column header (Name, Description, Rows, Columns, Tags) to sort ascending;
click again to flip to descending. The active column shows an up/down
arrow; the others are unsorted.

- **`datasetapp/templates/datasetapp/all_datasets.html`**: header `<td>`s
  promoted to `<th scope="col">` wrapping a `<button class="col-sort">`,
  body cells annotated with `data-sort-key` + `data-sort-value` (lower-cased
  text for textual columns, raw integers for `Rows` / `Columns`, joined tag
  names for the tag column). Inline script reorders `<tr>` elements in
  place — no network calls, no re-render of the row body, and tag links
  stay clickable. Default order on load is the server-side `slug`
  ordering, marked `aria-sort="ascending"` on the Name column.
- **`datasetapp/templates/datasetapp/base.html`**: CSS for the new
  `.col-sort` button (full-width hit target, hover affordance) and the
  up/down/unsorted arrow indicator driven by `aria-sort` (mask-image SVG,
  inherits `currentColor` so it tracks light / dark theme).

Behaviour-preserving for visitors with JavaScript disabled: the table
still renders in the existing slug order and column header text remains
visible — only the click-to-sort affordance is lost.

## v1.5.1

Documentation-only follow-up to v1.4.0's S3 backup work. No code changes.

- **`docs/backup.md`**: new end-to-end backup runbook for a future
  maintainer. Covers AWS bucket creation, IAM user + scoped policy,
  access-key generation, the Hetzner-side AWS CLI v2 install, `.env`
  population, smoke-test, S3 verification, cron install, nightly run
  verification, restore drill, full disaster recovery, and a
  troubleshooting block.
- **CLAUDE.md** *Backups → Host prerequisite*: the previous `sudo apt
  install awscli` line was wrong on Ubuntu 24.04 (the `awscli` apt
  package was dropped). Replaced with `sudo snap install aws-cli
  --classic` (the supported v2 path on Ubuntu 24.04) and a cross-link
  to `docs/backup.md` for the full runbook.

## v1.5.0

Security audit and hardening pass. Behaviour-preserving for normal visitors;
removes a stored-XSS surface, two reliability cliffs in the public download
path, and adds browser-side defence-in-depth headers. Full audit record in
`docs/SECURITY.md`.

### Highlights

- **Stored XSS removed** — `dataset_info.html` no longer applies `|safe` to
  admin-authored `name`, `description`, or `data_source`. A new
  `sanitise_markup` template filter (`datasetapp/templatetags/extra_tags.py`)
  passes the two text fields through `bleach` with a small tag/attribute
  allowlist (`a, b, i, em, strong, sub, sup, code, br, p, span, ul, ol, li,
  dl, dt, dd`); LaTeX in `\(...\)` still renders via MathJax. The contradictory
  `|safe|escape` chain on `special_message` is removed entirely — the
  homepage intro markup is now inlined in `all_datasets.html`.
- **`download_dataset` reliability** — input is now validated against
  `^[a-z0-9-]+\.[a-z]{3}$` before any DB lookup, so requests like
  `/file/foo`, `/file/foo.bar.csv`, or `/file/.csv` return 404 instead of
  raising `ValueError → 500`. `split(".")` was replaced with `rsplit(".", 1)`.
- **CSV preview ReDoS removed** — `_csv_preview` no longer calls
  `csv.Sniffer().sniff(...)`, which had catastrophic-backtracking behaviour
  on adversarial input and was reachable from any visitor hitting a detail
  page. The default `csv.excel` dialect is used unconditionally.
- **`_download_series` cached** — the 365-day per-dataset aggregation is
  now cached for one hour via `django.core.cache`, removing the
  unbounded-scan-per-request future-DoS as the `Hit` table grows.
- **File upload validation** — `DataFile.link_to_file` gains a
  `FileExtensionValidator(["csv","xls","xlsx","xml","mat"])`, and
  `DataFile.clean()` rejects mismatches between the declared `file_type`
  and the actual extension. Stops an admin from uploading `.html` masquerading
  as `.csv`.
- **Admin tightened** — `list_per_page` reduced from 2000 to 100 on all
  three admins. `HitAdmin` gains `readonly_fields = ("dataset_hit",
  "date_and_time")` (audit log, append-only), plus `date_hierarchy` +
  `list_filter` so scoping doesn't require loading the whole table.
- **Security headers** — new `openmv.middleware.SecurityHeadersMiddleware`
  emits `Content-Security-Policy`, `Permissions-Policy`, and
  `Cross-Origin-Opener-Policy: same-origin`. The CSP keeps `'unsafe-inline'`
  for `script-src` / `style-src` because `base.html` and `dataset_info.html`
  inline both today; externalising those is the follow-up that lets us drop
  the relaxation.
- **Cookie flags** — `prod.py` now explicitly sets
  `SESSION_COOKIE_HTTPONLY`, `SESSION_COOKIE_SAMESITE = "Lax"`,
  `CSRF_COOKIE_HTTPONLY`, `CSRF_COOKIE_SAMESITE = "Lax"`. Matches Django
  defaults but is now documented and immune to upstream default changes.
- **Upload limits** — `base.py` adds `DATA_UPLOAD_MAX_MEMORY_SIZE`,
  `FILE_UPLOAD_MAX_MEMORY_SIZE` (both 5 MiB), and `FILE_UPLOAD_PERMISSIONS = 0o644`.
- **CDN scripts pinned** — MathJax `2.7.9` and ECharts `5.5.1` instead of
  the floating `mathjax@2` / `echarts@5`. SRI hashes can be added with
  `make sri` once a network-connected maintainer runs it (the templates
  ship with `crossorigin="anonymous"` already in place).
- **Supply chain** — `Dockerfile` pins `ghcr.io/astral-sh/uv` to `0.8.17`
  instead of `:latest`. `ci.yml` adds `permissions: contents: read` and a
  non-blocking `pip-audit` step. `pyproject.toml` adds lower bounds to the
  three previously unpinned runtime deps and adds `pip-audit` to the dev
  group.
- **Tests** — new `datasetapp/tests/test_security.py` pins each finding so
  future refactors can't quietly re-open them: bleach allowlist behaviour,
  detail-page rendering, `download_dataset` 404 paths, `DataFile.clean`,
  `_csv_preview` error path, security-header presence, cache behaviour,
  removed `special_message` context.
- **Docs** — `docs/SECURITY.md` is now the canonical security record:
  full audit table (severity, file:line, status), host-side recommendations
  (Caddy admin rate-limit, Cloudflare WAF, fail2ban), and the vulnerability
  reporting paragraph. Top-level `SECURITY.md` points GitHub's "Security"
  tab at it. CLAUDE.md updated to match.

### Operational notes

- **SRI hashes are pending**: `make sri` prints the values to insert into
  the two CDN `<script>` tags. Documented as a one-line follow-up edit.
- **GitHub Actions are still tag-pinned** (`@v4`, `@v6`); SHA-pinning is
  documented as a follow-up issue (`docs/SECURITY.md` issue J).
- **HSTS preload** is intentionally not flipped on yet — the staged
  rollout in `prod.py`'s comment still applies.

## v1.4.0

Off-host backups to AWS S3 — closes #49 and replaces the frozen Linode
`backup-datasets.sh` cron that had been backing up a stale copy since the
2026-05-03 Hetzner cutover.

### Highlights

- **`bin/backup-openmv.sh`** (#49): a single host-side bash script that
  runs nightly under `deploy` from cron. On every invocation it:
  - dumps Postgres via `docker compose exec -T db pg_dump --clean
    --if-exists`, gzips the result, and uploads it to
    `s3://$BACKUP_S3_BUCKET/$BACKUP_S3_PREFIX/db/daily/db_openmv-YYYY-MM-DD.sql.gz`;
  - promotes the same dump to `db/monthly/db_openmv-YYYY-MM.sql.gz` on the
    1st of each month and to `db/yearly/db_openmv-YYYY.sql.gz` on Jan 1
    via a server-side `aws s3 cp` (no second `pg_dump`);
  - mirrors `data/media/` and `data/public/` to the matching S3 prefixes
    via `aws s3 sync` *without* `--delete`, so an accidental local rm or a
    detached bind-mount doesn't propagate to the off-host copy;
  - prunes `db/daily/` to the 15 most recent objects and `db/monthly/` to
    the 12 most recent, by S3 `LastModified`. `db/yearly/` is never pruned.
  Replaces the old `manage.py dumpdata`-based script — `pg_dump` is faster
  on the ~300k-row `Hit` table and round-trips cleanly across Django
  versions.
- **AWS S3, deliberately not Hetzner Object Storage**: the destination
  sits in a different cloud account from the production VPS so a
  compromise of one doesn't reach the other.
- **`data/static/` is intentionally skipped**: `collectstatic` regenerates
  it on every container start, so it has nothing worth preserving.
- **`.env.example`**: five new commented-out keys
  (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`,
  `BACKUP_S3_BUCKET`, `BACKUP_S3_PREFIX`). The script sources the same
  `.env` the prod stack uses, so secrets stay in one place.
- **CLAUDE.md** gains a `## Backups` section (S3 layout, IAM scope, host
  `awscli` install, cron entry, restore commands) and a new Gotcha (#7)
  documenting the deliberate `data/static/` skip.

The cron entry itself is **not** auto-installed — it lives outside the
repo as operational state, documented in CLAUDE.md so the next maintainer
knows where to put it. No visitor-visible behaviour change.

## v1.3.0

Privacy fix for the `Hit` table — closes #17 and clears the last
remaining D-batch item in the modernization roadmap (#42).

### Highlights

- **Hit schema trimmed** (#17): `datasetapp.models.Hit` no longer stores
  `UA_string`, `IP_address`, or `referrer`. The table is now
  `(id, dataset_hit_id, date_and_time)` — exactly the columns the public
  site uses to render the per-dataset download counter and the 365-day
  sparkline (`_download_series` in `datasetapp/views.py` groups rows by
  `TruncDate("date_and_time")`). The `download_dataset` view writes one
  row per download via `Hit(dataset_hit=file_obj).save()`; the unused
  `get_IP_address` helper was removed.
- **Migration `0002_drop_hit_pii`** runs three `RemoveField` ops on the
  `Hit` model. On any database that pre-dates this release, applying the
  migration drops the columns and destroys all legacy IP / UA / referrer
  values in one step — there is no separate retention job because the
  schema itself no longer holds PII.
- **Admin tightened** (`datasetapp/admin.py`): `HitAdmin.list_display`
  and `list_filter` only reference the surviving columns. Admin users no
  longer see PII because the database no longer holds any.
- **Tests**: `Hit.objects.create(...)` calls in
  `datasetapp/tests/test_views.py` updated to the trimmed schema; the
  365-day sparkline assertion (`sum(point[1] for point in series) == 1`)
  still passes against the new model.
- **CLAUDE.md** + **README.md**: the "Models" line and the README
  bullet now describe the privacy posture of the `Hit` table; a Gotcha
  documents the migration as the place legacy PII gets dropped.

No visitor-visible behaviour change — both the count and the sparkline
render identically. Download history is preserved indefinitely; only the
PII columns go away.

## v1.2.0

Django bumped from 4.2 LTS to 5.2 LTS, closing the E1 item on the
modernization roadmap (#42). Django 4.2 LTS reaches EOL in April 2026;
5.2 LTS (released April 2025) is the current LTS series and keeps the
project on the same LTS-only cadence.

### Highlights

- **Django 5.2 LTS** (#35): `pyproject.toml` pin moved from `>=4.2,<5.0`
  to `>=5.2,<5.3`; `uv.lock` refreshed (django 4.2.30 → 5.2.13). The
  smoke test suite (`datasetapp/tests/test_views.py`) passes unchanged
  against 5.2; `manage.py check` and `manage.py check --deploy` report
  no new warnings beyond the pre-existing `SECURE_HSTS_PRELOAD=False`
  (deliberate staged HSTS rollout from C3). No code changes were needed
  — the pre-flight audit found no usage of the APIs Django 5.x removed
  (`USE_L10N`, `django.utils.timezone.utc`, `index_together`, etc.).
- **CLAUDE.md**: the "Tooling" section now reflects the new pin and notes
  the bump rationale; the "Outstanding work" referent (#35) is now closed.

## v1.1.1

Documentation cleanup: bring `README.md`, `CLAUDE.md`, and the
`docker-compose.prod.yml` comments back into sync with the production stack.

- `README.md`: the production-notes paragraph still claimed "the live site
  has Apache serving `/static/` and `/media/` directly" and that "in
  production Apache must be configured to intercept `/media/`" — both stale
  since the May 2026 Hetzner cutover, when host-installed Caddy took over
  TLS, static files, and `/media/` from Apache on Linode. Updated to refer
  to Caddy and to the `data/static/` + `data/media/` bind mounts; also
  corrected the dev-server condition from the legacy `DJANGO_DEBUG=1` to
  the actual `DEBUG=True`.
- `CLAUDE.md` + `docker-compose.prod.yml`: rewrote the `.env` bind-mount
  paragraph and the matching compose comment. Both still implied the
  bind-mount was required because `openmv/settings/base.py` read the file
  at import time. After #22 landed (PR #60), settings read `os.environ`
  first, and `env_file: .env` in the compose file already exposes every
  key as a process env var. The bind-mount is now a redundant fallback for
  the `dotenv_values()` codepath, not a requirement.

No behaviour change — docs only, hence PATCH.

## v1.1.0

CI now runs the test suite against Postgres 16 to match production, closing
the C4 item on the modernization roadmap (#42).

### Highlights

- **Postgres in CI** (#30): `.github/workflows/ci.yml` boots a
  `postgres:16-alpine` service container and points pytest at a new
  `openmv.settings.ci` module. The new module derives from `prod.py` —
  Postgres engine, `DEBUG=False`, the same `POSTGRES_*` + `SQL_*` env-var
  contract — but disables `SECURE_SSL_REDIRECT`, HSTS, and the
  secure-cookie flags so the Django test client (which speaks plain HTTP)
  doesn't get 301-redirected on every request. Postgres-only behaviour
  (datatypes, transaction semantics, parameter quoting, migrations) is now
  exercised by the smoke suite on every push and PR.
- **Versioning policy**: CLAUDE.md gains a "Versioning and releases"
  section codifying the every-PR `pyproject.toml` + `RELEASES.md` bump
  rule, the patch/minor/major heuristic, and the requirement to ask the
  human reviewer (or `AskUserQuestion` when running as Claude Code) when
  unsure. Tag + GitHub Release continue to be produced automatically by
  `release.yml`.

## v1.0.0

First tagged release. Captures the 2026 modernization of the long-standing
codebase that powers <https://openmv.net> — the docs, repo hygiene, tooling,
and CI work needed to make further development safe.

### Highlights

- **Docs**: added `README.md`, `CLAUDE.md`, and `LICENSE`. CLAUDE.md is the
  canonical orientation for new contributors and points at the GitHub issue
  tracker for outstanding work.
- **Dependency management**: `requirements.txt` removed in favour of
  `pyproject.toml` + `uv.lock`. Django pinned `>=4.2,<5.0`. Python 3.11 pinned
  via `.python-version`.
- **CI/CD foundation**: `.github/workflows/ci.yml` runs `pre-commit` and
  `pytest` on every push and PR.
- **Smoke tests**: `datasetapp/tests/test_views.py` covers the homepage, tag
  filter, dataset detail, and download redirect paths via `pytest-django`.
- **Local Docker**: `Dockerfile` (multi-stage uv builder + gunicorn runtime)
  and `docker-compose.yml` for dev parity with prod's Postgres backend.
  Production still ships behind Apache.
- **Pre-commit hygiene**: `flake8` hook moved from `gitlab.com` to GitHub;
  `click<8.1` pinned to keep the legacy `black==21.12b0` hook working until
  the broader hook refresh lands.
- **Bug fixes**: corrected the broken `%`-format log call in
  `about_dataset` that swallowed dataset slugs in the log output.
- **Repo conventions**: added `.editorconfig` so editors agree on
  indentation, line endings, and trailing whitespace without per-editor
  setup.

### Versioning

From here, the project follows semver:

- **PATCH** for bugfixes and dependency security bumps.
- **MINOR** for additive features (new views, template tweaks, schema
  additions).
- **MAJOR** for URL or template structure breaks.

### How v1.0.0 was tagged

Once the v1.0.0-prep PR was merged to `master`:

```
git checkout master && git pull
git tag -a v1.0.0 -m "v1.0.0"
git push origin v1.0.0
```

A matching GitHub Release was published at
<https://github.com/kgdunn/Django-dataset-download-app/releases/tag/v1.0.0>
with the contents of this section as the release body.
