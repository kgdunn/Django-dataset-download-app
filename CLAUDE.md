# CLAUDE.md

Orientation for Claude Code (and any other future maintainer) working in this repository. Keep this file up-to-date as the codebase evolves.

## What this repo is

The Django site behind <https://openmv.net> — a dataset catalogue that lists, describes, and serves downloads of small real-world datasets used in the textbook *Process Improvement using Data*. Originally written in 2010, ported to Python 3 / Django 3.2 in 2022, migrated from Linode + Apache + mod_wsgi to Hetzner + Caddy + Docker Compose in May 2026. Currently in production.

**The live site cannot break.** Favour additive, behaviour-preserving changes. A staging hostname `test.openmv.net` resolves to the same Hetzner host (DNS-only in Cloudflare); use it before pushing changes that could affect what visitors see.

## Project shape

- **Project**: `openmv/` (settings package, URL conf, WSGI/ASGI). Settings live under `openmv/settings/` — `base.py` (shared), `dev.py` (local SQLite + DEBUG=True), `prod.py` (Postgres + DEBUG=False + Caddy proxy headers), `ci.py` (GitHub Actions — derives from `prod.py` and disables HTTPS-only middleware so the Django test client works).
- **App**: `datasetapp/` (the only app).
- **Models** (`datasetapp/models.py`): `Tag`, `Dataset`, `DataFile`, `Hit`.
  - `Dataset` ↔ `Tag` is many-to-many.
  - `Dataset` ↔ `DataFile` is one-to-many (a dataset can have CSV + XLS + XML + MAT siblings).
  - `Hit` records one download. Since v1.3.0 (#17) the table holds only `(dataset_hit, date_and_time)` — no IP, User-Agent, or referrer is captured. Two columns power three visible features: the per-dataset count on the detail page, the sortable Downloads column on the homepage / tag-filter list (v1.7.0, via a `Count("datafile__hit", distinct=True)` annotation in `_annotate_with_downloads`; desktop-only — the mobile card layout hides it), and the 365-day sparkline on the detail page (`_download_series` in `datasetapp/views.py` groups rows by `TruncDate("date_and_time")`). Rows are kept indefinitely; the per-row history is fine to retain because no PII is stored.
- **Views** (`datasetapp/views.py`):
  - `display_all` — `/` — homepage table. Optional `?q=<terms>` substring search across dataset `name`, `description`, `data_source`, `author_name`, and tag `name` / `description` (whitespace-AND tokens, ORed across fields, `icontains` so SQLite dev and Postgres prod behave identically; v1.8.0, issue #94). Empty / missing `q` returns the full table.
  - `display_by_tag` — `/tag/<slug>` — filter by tag.
  - `about_dataset` — `/info/<slug>` — detail page.
  - `download_dataset` — `/file/<name>.<ext>` — increments a `Hit` row, then streams the file body via `FileResponse` (with `Content-Disposition: attachment; filename=<name>.<ext>`). Until v1.6.4 it 302-redirected to the matching `/media/datasets/...` URL and let Caddy serve the bytes, but that doubled the surface exposed to Cloudflare's Bot Fight Mode and 403'd `urllib`/`pandas.read_csv` clients (issue #86). Caddy still serves `/media/*` directly for any pre-existing direct links; only the public `/file/*` path streams through gunicorn.
- **Templates** (`datasetapp/templates/datasetapp/`):
  - `base.html` — Bootstrap 3 layout, inline `<style>`, no static-file dependency. Loads ECharts (CDN) for the detail-page sparkline.
  - `all_datasets.html` — the list page.
  - `dataset_info.html` — the detail page. Pulls in MathJax for any LaTeX in descriptions, renders a 365-day downloads sparkline (ECharts) below the download counter, a Python quickstart code block with a copy-to-clipboard button (rendered when a CSV file exists), an inline CSV preview table (first 10 rows) above the download block, and prev/next dataset links at the bottom.
- **Custom template tags**: `datasetapp/templatetags/extra_tags.py` defines two filters — `slice_string` (trims filenames) and `sanitise_markup` (passes admin-authored HTML through `bleach` with a small allowlist before rendering — see `docs/SECURITY.md` finding 1).
- **Project-local middleware**: `openmv/middleware.py` defines `SecurityHeadersMiddleware`, which sets `Content-Security-Policy`, `Permissions-Policy`, and `Cross-Origin-Opener-Policy` on every response. Wired into `MIDDLEWARE` in `base.py` immediately after Django's `SecurityMiddleware`.
- **Admin**: registered in `datasetapp/admin.py` with `list_per_page = 100`. `HitAdmin` rows are `readonly_fields` (the table is an append-only audit log) and have a `date_hierarchy` + `list_filter` so scoping doesn't require loading the whole table.

## How it runs

- `make debug` runs `collectstatic --no-input`, `migrate`, `createcachetable`, then `runserver 8080 --nostatic`.
- Settings read **process environment first**, then fall back to a `.env` file via `python-dotenv` if one exists. The `env()` and `env_list()` helpers in `openmv/settings/base.py` encapsulate this. `SECRET_KEY` is the only universally required key; `prod.py` additionally requires the `POSTGRES_*` + `SQL_*` keys. Either layer (env or `.env`) can supply them — handy for containers, CI, and ad-hoc overrides.
- Which DB / hosts / DEBUG flag you get depends on `DJANGO_SETTINGS_MODULE`:
  - `openmv.settings.dev` (default in `manage.py`, `wsgi.py`, `asgi.py`, `pyproject.toml` pytest) → SQLite at `db.sqlite3`, `DEBUG=True`, `ALLOWED_HOSTS` from `$ALLOWED_HOSTS` (default `127.0.0.1,localhost`).
  - `openmv.settings.prod` (forced by `docker-compose.prod.yml`'s `web.environment` block) → Postgres via `POSTGRES_*` + `SQL_*` keys, `DEBUG=False`, `ALLOWED_HOSTS` from `$ALLOWED_HOSTS` (default `.openmv.net,127.0.0.1`), `SECURE_PROXY_SSL_HEADER` + `CSRF_TRUSTED_ORIGINS` for Caddy.
  - `openmv.settings.ci` (forced by `.github/workflows/ci.yml` for the pytest step) → re-exports prod, then turns off `SECURE_SSL_REDIRECT` / HSTS / secure-cookie flags so the Django test client (which uses HTTP) doesn't hit a 301. Same Postgres `POSTGRES_*` + `SQL_*` env vars as prod, supplied by the workflow against the `postgres:16-alpine` service.

## Running locally

Two paths:

**Native (uv):**
```bash
cp .env.example .env   # edit SECRET_KEY
uv sync --dev
make debug             # collectstatic + migrate + createcachetable + runserver:8080
```

**Docker compose (`make docker-up` → SQLite + runserver in a container):**
```bash
cp .env.example .env   # set SECRET_KEY
make docker-up         # docker compose up --build
```
Both paths use `openmv.settings.dev` and serve <http://127.0.0.1:8080/>. To rehearse the production stack (Postgres + gunicorn + `openmv.settings.prod`), use `docker compose -f docker-compose.prod.yml up --build` instead.

## Production deployment (Hetzner)

Architecture:

```
Cloudflare (proxied, orange cloud) ──HTTPS──> Caddy on Hetzner host (TLS terminator + static)
                                                ├── /static/*          → ./data/static/  (file_server)
                                                ├── /media/*           → ./data/media/   (file_server)
                                                ├── /robots.txt etc.   → ./data/public/
                                                └── everything else    → 127.0.0.1:8001 → gunicorn (Docker)
                                                                                          └── postgres (Docker, 127.0.0.1:5434)
```

- **VPS**: Hetzner Cloud, Ubuntu 24.04, Nuremberg. Same VPS hosts other apps (e.g. Factori.al under `/home/deploy/factorial/`); the openmv stack coexists via offset ports and a shared host-installed Caddy.
- **Code path**: `/home/deploy/openmv/repo/` — git checkout of `master`.
- **Compose file**: `docker-compose.prod.yml` runs two services bound to loopback only — `web` (gunicorn on `127.0.0.1:8001`) and `db` (`postgres:16-alpine` on `127.0.0.1:5434`).
- **Compose project name**: both compose files pin `name: openmv` at the top (v1.8.2). Load-bearing for sibling-stack isolation — without it Compose defaults the project name to the directory basename `repo`, which collides with the literature stack at `/home/deploy/literature/repo/` (a `down` in either repo would tear out the other's containers). It's also load-bearing for the Postgres volume on disk: Compose names every volume `<project>_<volume>`, so the data lives in **`openmv_openmv_postgres_data`**. See gotcha #11 below for the migration shape if the project name ever changes again.
- **Bind-mounted data dirs** (under `/home/deploy/openmv/repo/data/`):
  - `media/` — Django uploads served by Caddy and mounted into the container as `/app/media`.
  - `static/` — `collectstatic` output, mounted as `/app/static`. Re-populated by the `web` container's startup command.
  - `public/` — host the small files Apache used to alias (`robots.txt`, `favicon.ico`, `blender-efficiency.xlsx`).
- **`.env`** is loaded into the container's process environment via `env_file: .env` in `docker-compose.prod.yml`, and the same file is also bind-mounted at `/app/.env:ro`. Since #22 landed (PR #60), `openmv/settings/base.py` reads `os.environ` first, so the bind-mount is no longer required — `env_file:` already exposes every key as an env var. The bind-mount is kept as a redundant fallback for the `dotenv_values()` codepath; an equally valid setup is to drop it and rely solely on `env_file:` (or move the keys into `web.environment` directly). Never commit `.env`.
- **`DJANGO_SETTINGS_MODULE=openmv.settings.prod`** is set on the `web` service in `docker-compose.prod.yml`; this is what selects the prod-only DB / hosts / proxy headers. Don't rely on the `manage.py` default for production.
- **Caddy config**: `/etc/caddy/Caddyfile` on the host. Reload with `sudo systemctl reload caddy` (validate first with `sudo caddy validate --config /etc/caddy/Caddyfile`).
- **TLS**:
  - `openmv.net` and `www.openmv.net` use a **Cloudflare Origin Certificate** (15-year, signed by Cloudflare's internal CA) at `/etc/caddy/origin-certs/openmv.net/`. Cloudflare's edge serves a public-trusted cert to visitors and re-encrypts to origin in `Full (strict)` mode.
  - `test.openmv.net` uses Caddy-managed Let's Encrypt. It must stay **DNS-only** (grey cloud) in Cloudflare so the HTTP/TLS challenge can reach origin directly.
- **Auto-deploy**: every push to `master` fires `.github/workflows/deploy.yml`, which SSHes into Hetzner and triggers `bin/deploy-impl.sh`. The deploy script runs `docker compose -f docker-compose.prod.yml up -d --build` (which in turn runs `migrate --noinput` + `collectstatic --noinput` on container start, then boots gunicorn) and sanity-curls `127.0.0.1:8001`.
- **Manual deploy** (rollback, hotfix, debugging): from `/home/deploy/openmv/repo/`, run `git pull && docker compose -f docker-compose.prod.yml up -d --build` directly.
- **Public IPs**: IPv4 `178.104.167.195`, IPv6 `2a01:4f8:1c19:2380::1`. Behind Cloudflare's anycast for the apex; visible directly only for `test.openmv.net`.

## Backups

Off-host backups go to AWS S3 — deliberately a different cloud provider /
account from the Hetzner VPS so a compromise of one doesn't reach the other.
The Hetzner-side script is `bin/backup-openmv.sh`; it runs nightly under
`deploy` from cron and does three things on every invocation:

1. **Postgres dump** of the running `db` container via
   `docker compose -f docker-compose.prod.yml exec -T db pg_dump --clean --if-exists`,
   gzipped, uploaded to
   `s3://$BACKUP_S3_BUCKET/$BACKUP_S3_PREFIX/db/daily/db_openmv-YYYY-MM-DD.sql.gz`.
   The same dump is also copied to `db/monthly/db_openmv-YYYY-MM.sql.gz` on
   the 1st of each month, and to `db/yearly/db_openmv-YYYY.sql.gz` on Jan 1.
2. **`aws s3 sync`** of `data/media/` → `…/media/` and `data/public/` →
   `…/public/`. No `--delete` flag — an accidental local rm or detached bind
   mount must not propagate to the off-host copy. `data/static/` is
   intentionally **not** backed up because `collectstatic` regenerates it on
   every container start.
3. **Retention pruning** by S3 `LastModified`: `db/daily/` keeps the 15
   most recent objects, `db/monthly/` keeps 12, `db/yearly/` is never pruned.

S3 layout:

```
s3://$BACKUP_S3_BUCKET/$BACKUP_S3_PREFIX/
├── db/
│   ├── daily/    db_openmv-2026-05-04.sql.gz   (≤15)
│   ├── monthly/  db_openmv-2026-05.sql.gz      (≤12)
│   └── yearly/   db_openmv-2026.sql.gz         (∞)
├── media/        mirror of data/media/
└── public/       mirror of data/public/
```

### Configuration

`bin/backup-openmv.sh` sources the same `.env` the prod stack uses. The
keys it needs on top of the existing `POSTGRES_*` set:

```
AWS_ACCESS_KEY_ID=…
AWS_SECRET_ACCESS_KEY=…
AWS_DEFAULT_REGION=eu-central-1
BACKUP_S3_BUCKET=openmv-backups
BACKUP_S3_PREFIX=openmv
```

The IAM principal those keys belong to should be scoped to `s3:PutObject`,
`s3:GetObject`, `s3:DeleteObject`, and `s3:ListBucket` on
`arn:aws:s3:::$BACKUP_S3_BUCKET/$BACKUP_S3_PREFIX/*` only — nothing else.
Enable bucket versioning + SSE-S3 (default since Jan 2023) when creating
the bucket.

### Host prerequisite

The Hetzner VPS needs the AWS CLI v2 on the host (not in the container —
the script calls `aws` directly). On Ubuntu 24.04 the `awscli` apt
package is gone; use snap instead: `sudo snap install aws-cli --classic`.
Full step-by-step (AWS bucket + IAM, Hetzner install, smoke-test, restore
drill, troubleshooting) is in [`docs/backup.md`](docs/backup.md).

### Cron entry (run as `deploy`)

```
35 21 * * *  /home/deploy/openmv/repo/bin/backup-openmv.sh \
    >> /home/deploy/openmv/backups/backup.log 2>&1
```

Same time the Linode cron used to run. The script is *not* installed
automatically by `bin/deploy-impl.sh`; cron lives outside the repo because
its presence and schedule are operational state, not application state.

### Restore

```bash
# Database (daily snapshot)
aws s3 cp s3://$BACKUP_S3_BUCKET/openmv/db/daily/db_openmv-YYYY-MM-DD.sql.gz - \
  | gunzip \
  | docker compose -f docker-compose.prod.yml exec -T db \
      psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

# Datasets (pull missing files back; --delete deliberately omitted)
aws s3 sync s3://$BACKUP_S3_BUCKET/openmv/media/ data/media/
aws s3 sync s3://$BACKUP_S3_BUCKET/openmv/public/ data/public/
```

`data/static/` is rebuilt automatically by the next container start —
don't restore it.

## Gotchas worth knowing before editing

1. **`DatasetManager.get_queryset` filters out `is_hidden=True` rows from the public site _and_ from the admin list.** `Dataset.objects` is the only manager, so the admin's `DatasetAdmin` queryset is filtered too. To re-edit a hidden dataset, flip `is_hidden` directly in the DB (`./manage.py shell` or a `psql` session) — there is no `all_objects` escape hatch.
2. **`download_dataset` opens the file from `MEDIA_ROOT` and streams it with `FileResponse`.** No redirect to `/media/...` happens any more (since v1.6.4 / issue #86), so the file just needs to be readable by the gunicorn worker — in production via the `/app/media` bind mount, locally via `BASE_DIR/media/`. Caddy's `/media/*` `file_server` rule is still in place for any externally-cached direct links, but the public site no longer points at those URLs. Tests need a real file under `MEDIA_ROOT` (the `csv_file` fixture in `datasetapp/tests/test_views.py` writes one to `tmp_path` and overrides `settings.MEDIA_ROOT`).
3. **`DataFile.link_to_file` values stored in the DB are `datasets/<file>.<ext>`** (no leading `media/`). Linode's legacy data had a `media/` prefix that was stripped during the Hetzner cutover. If you ever re-restore from a stale Linode dump, re-run: `UPDATE datasetapp_datafile SET link_to_file = regexp_replace(link_to_file, '^media/', '') WHERE link_to_file LIKE 'media/%';`
4. **`DataFile.objects.filter(...)[0]` in `download_dataset`** still uses `[0]` indexing inside a `try/except IndexError`. If you "tidy" it to `.first()`, preserve the same 404 path. (The two `Dataset.objects.filter(...)[0]` siblings have already been migrated to `.first()` + `None` check.)
5. **`download_dataset` validates its `file_name` against `^[a-z0-9-]+\.[a-z]{3}$` before any DB lookup.** Anything outside that shape returns 404, not 500. If you ever need to support a 4-letter extension (`.json`, `.tsv`, …), update both `_DOWNLOAD_FILENAME_RE` *and* the `DataFile.file_type_choice` tuple in the same change.
6. **Admin-authored markup in `Dataset.description` and `Dataset.data_source` is passed through `bleach` at render time** by the `sanitise_markup` filter. Tags outside the allowlist (script, iframe, style, event handlers, javascript: URLs) are stripped. LaTeX in `\(...\)` survives because bleach treats backslashes and dollar signs as text. If you add a new field that should accept the same markup, route it through the same filter — don't reach for `|safe`.
7. **The `datasetapp` logger is configured by the `LOGGING` dict in `openmv/settings/base.py`** and writes to stdout via a `StreamHandler`. In the production Docker container that means `docker logs` (and any host log shipper) captures everything; locally it streams to the `runserver` terminal. Override the level for ad-hoc debugging by setting `DATASETAPP_LOG_LEVEL=DEBUG` in `.env` or the process env.
8. **`bin/backup-openmv.sh` deliberately skips `data/static/`.** It mirrors `data/media/` (datasets — the irreplaceable bytes) and `data/public/` (the small Apache-era files), but `collectstatic` regenerates `data/static/` on every container start, so backing it up would just be padding. If you ever add a file under `data/static/` that *isn't* `collectstatic` output, fix the source — don't extend the backup script.
9. **Migration `0002_drop_hit_pii` is what destroys legacy IP / User-Agent / referrer data** in any database that pre-dates v1.3.0 — the columns are dropped, taking every existing value with them. There is no separate retention job because the schema itself no longer holds PII. If you ever restore a pre-v1.3.0 backup, re-run `manage.py migrate` to re-trim it.
10. **Security review of the codebase lives in `docs/SECURITY.md`** — that's the canonical record of every audit finding (fixed and deferred), the host-side recommendations (Caddy admin rate-limit, Cloudflare WAF, fail2ban), and the follow-up issues. Update it on any PR that touches a security-relevant surface (templates with markup, view input handling, file uploads, settings, middleware, dependencies, CI permissions).
11. **`name: openmv` in both compose files is load-bearing — don't remove it.** It pins the Compose project name. Without it, Compose defaults the project name to the basename of the invoking directory (`repo` for `/home/deploy/openmv/repo/`); the sibling literature stack at `/home/deploy/literature/repo/` resolves to the same default, which means `docker compose -f docker-compose.prod.yml down` from either repo tears out the other stack's containers (literally observed on 2026-05-09 — `openmv-app` + `openmv-postgres` were getting wiped during literature operations until the pin landed in v1.8.2). The pin also fixes the on-disk Postgres volume name: Compose names volumes `<project>_<volume>`, so renaming the project also renames the volume, and the new compose mounts a fresh empty volume while the old data sits orphaned. The volume currently lives at `openmv_openmv_postgres_data`. If you ever rename the project (or unpin `name:`), migrate the data **before** the new stack boots: stop/rm the old containers without `-v`, `docker volume create <new>_openmv_postgres_data`, then `docker run --rm -v <old>:/from:ro -v <new>:/to alpine cp -a /from/. /to/`, then `docker compose up -d --build`. The 2026-05-09 migration moved `repo_openmv_postgres_data` → `openmv_openmv_postgres_data` this way. Bind mounts (`data/media`, `data/static`, `data/public`) survive a project rename untouched — they're addressed by host path, not by volume name.

## Tooling

- **Dependencies** are managed with [uv](https://docs.astral.sh/uv/). The source of truth is `pyproject.toml` + the committed `uv.lock`. There is no `requirements.txt`.
  - Install everything: `uv sync --dev`
  - Add a runtime dep: `uv add <pkg>`; dev dep: `uv add --dev <pkg>`
  - Refresh the lockfile after manual edits: `uv lock`
  - Audit installed deps for known CVEs: `uv run pip-audit` (added to dev group in v1.5.0; CI runs it non-blocking).
  - Django is pinned `>=5.2,<5.3` (bumped from 4.2 LTS in v1.2.0). 5.2 is the current LTS series; the project intentionally tracks LTS releases only.
  - Runtime deps include `bleach` (v1.5.0+) for HTML sanitisation in the `sanitise_markup` template filter.
- **Tests** run with `uv run pytest` (or `make test`). `pytest-django` is wired through `[tool.pytest.ini_options]` in `pyproject.toml`. Smoke suite lives in `datasetapp/tests/test_views.py`.
- **GitHub Actions** runs `pre-commit run --all-files` and `pytest` on every PR and on push to `master` (`.github/workflows/ci.yml`). The pytest step boots a `postgres:16-alpine` service container, sets `DJANGO_SETTINGS_MODULE=openmv.settings.ci`, and injects `SECRET_KEY` + `POSTGRES_*` + `SQL_*` env vars directly via the workflow `env:` block — no `.env` file is created. Tests therefore run against the same database engine as production, catching Postgres-only behaviour that SQLite would silently paper over.
- **Docker compose**: `docker-compose.yml` is for **local development** (volume-mounts the source for hot reload, runs `runserver` against SQLite via `openmv.settings.dev`). `docker-compose.prod.yml` is the **production** compose used on Hetzner (bind-mounts `.env` and `data/` dirs, sets `DJANGO_SETTINGS_MODULE=openmv.settings.prod`, runs `migrate` + `collectstatic` + `gunicorn`, binds to loopback on offset ports `8001`/`5434`). Both use the same `Dockerfile`.
- **pre-commit** is configured (`.pre-commit-config.yaml`) — hooks are kept on current stable releases (`pre-commit-hooks` v5, `mypy` v1.13, `isort` 5.13, `black` 24.10, `blacken-docs` 1.19, `flake8` 7.1). Refresh with `pre-commit autoupdate` and re-run `pre-commit run --all-files` before merging.
- **flake8** config: `.flake8`. Line length 100. Ignores E266/E203/E231/W503.

## Branch conventions

- Production deploys ship from `master`.
- Modernization work happens on `claude/modernize-legacy-repo-*` branches and is reviewed before merge.

## Versioning and releases

Every PR that changes runtime behaviour, dependencies, settings, CI, deploy
scripts, or public docs **must** bump `version` in `pyproject.toml` and add a
matching `## v<new-version>` section to `RELEASES.md` describing the change.
The version field is the trigger for the release pipeline — no bump means no
release.

Bump heuristic (anchors the policy stated in the v1.0.0 release notes):

- **PATCH** (`x.y.Z`) — bugfixes, dependency security bumps, infra-only
  tweaks with no user-visible behaviour change.
- **MINOR** (`x.Y.0`) — additive features, schema additions, new templates,
  new settings modules, CI parity work (e.g. Postgres-in-CI).
- **MAJOR** (`X.0.0`) — URL or template structure breaks, removal of public
  views, anything that could surprise an unsuspecting visitor.

If unsure which level to pick, **ask the human reviewer before merging.** When
running as Claude Code, ask via `AskUserQuestion` rather than guessing.

Tagging and the GitHub Release are produced automatically by
`.github/workflows/release.yml` once the bumped `pyproject.toml` and the
matching `RELEASES.md` section land on `master`. The workflow refuses to run
if the `## v<version>` heading is missing — that's the safety net. **Do not**
create tags manually.

## After opening a PR

Once a PR is posted, watch it. If `master` advances and the PR develops merge
conflicts, resolve them on the PR branch and push the merge commit — don't
leave the PR sitting in a conflicted state waiting for the human reviewer to
rebase. When the conflict is in `pyproject.toml` / `RELEASES.md` because
another PR landed a version bump, renumber your section to the next
appropriate level on top of the new `master` version (re-apply the PATCH /
MINOR / MAJOR heuristic above against the new base) and update any
`docs/SECURITY.md` "Fixed in vX.Y.Z" cross-references to match. Re-run
`pytest` and `pre-commit` after the merge before pushing.

## Outstanding work

The GitHub issue tracker is the single source of truth for outstanding work: <https://github.com/kgdunn/Django-dataset-download-app/issues>. Don't duplicate the list here — it goes stale.

## Keeping this file consistent

CLAUDE.md must stay consistent with the codebase. On any PR that touches `datasetapp/`, `openmv/`, `pyproject.toml`, `RELEASES.md`, `Makefile`, `.pre-commit-config.yaml`, or `.github/workflows/`, re-read this file before opening the PR and update anything that has drifted — Project shape, How it runs, Gotchas, Tooling, Branch conventions, Versioning and releases. If you're Claude Code, run this consistency check on every implementation task, not just when explicitly asked.
