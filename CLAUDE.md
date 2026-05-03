# CLAUDE.md

Orientation for Claude Code (and any other future maintainer) working in this repository. Keep this file up-to-date as the codebase evolves.

## What this repo is

The Django site behind <https://openmv.net> — a dataset catalogue that lists, describes, and serves downloads of small real-world datasets used in the textbook *Process Improvement using Data*. Originally written in 2010, ported to Python 3 / Django 3.2 in 2022, migrated from Linode + Apache + mod_wsgi to Hetzner + Caddy + Docker Compose in May 2026. Currently in production.

**The live site cannot break.** Favour additive, behaviour-preserving changes. A staging hostname `test.openmv.net` resolves to the same Hetzner host (DNS-only in Cloudflare); use it before pushing changes that could affect what visitors see.

## Project shape

- **Project**: `openmv/` (settings package, URL conf, WSGI/ASGI). Settings live under `openmv/settings/` — `base.py` (shared), `dev.py` (local SQLite + DEBUG=True), `prod.py` (Postgres + DEBUG=False + Caddy proxy headers).
- **App**: `datasetapp/` (the only app).
- **Models** (`datasetapp/models.py`): `Tag`, `Dataset`, `DataFile`, `Hit`.
  - `Dataset` ↔ `Tag` is many-to-many.
  - `Dataset` ↔ `DataFile` is one-to-many (a dataset can have CSV + XLS + XML + MAT siblings).
  - `Hit` records one download. Stores raw IP + UA + referrer.
- **Views** (`datasetapp/views.py`):
  - `display_all` — `/` — homepage table.
  - `display_by_tag` — `/tag/<slug>` — filter by tag.
  - `about_dataset` — `/info/<slug>` — detail page.
  - `download_dataset` — `/file/<name>.<ext>` — increments a `Hit` row, then 302-redirects to the media URL of the matching `DataFile`. The actual bytes are served by the front-end web server (Caddy in production), not by Django.
- **Templates** (`datasetapp/templates/datasetapp/`):
  - `base.html` — Bootstrap 3 layout, inline `<style>`, no static-file dependency. Loads ECharts (CDN) for the detail-page sparkline.
  - `all_datasets.html` — the list page.
  - `dataset_info.html` — the detail page. Pulls in MathJax for any LaTeX in descriptions, renders a 365-day downloads sparkline (ECharts) below the download counter, a Python quickstart code block with a copy-to-clipboard button (rendered when a CSV file exists), an inline CSV preview table (first 10 rows) above the download block, and prev/next dataset links at the bottom.
- **Custom template tag**: `datasetapp/templatetags/extra_tags.py` defines a `slice_string` filter used in templates to trim filenames.
- **Admin**: registered in `datasetapp/admin.py` with `list_per_page = 2000` (deliberate — small dataset count).

## How it runs

- `make debug` runs `collectstatic --no-input`, `migrate`, `createcachetable`, then `runserver 8080 --nostatic`.
- Settings read **process environment first**, then fall back to a `.env` file via `python-dotenv` if one exists. The `env()` and `env_list()` helpers in `openmv/settings/base.py` encapsulate this. `SECRET_KEY` is the only universally required key; `prod.py` additionally requires the `POSTGRES_*` + `SQL_*` keys. Either layer (env or `.env`) can supply them — handy for containers, CI, and ad-hoc overrides.
- Which DB / hosts / DEBUG flag you get depends on `DJANGO_SETTINGS_MODULE`:
  - `openmv.settings.dev` (default in `manage.py`, `wsgi.py`, `asgi.py`, `pyproject.toml` pytest) → SQLite at `db.sqlite3`, `DEBUG=True`, `ALLOWED_HOSTS` from `$ALLOWED_HOSTS` (default `127.0.0.1,localhost`).
  - `openmv.settings.prod` (forced by `docker-compose.prod.yml`'s `web.environment` block) → Postgres via `POSTGRES_*` + `SQL_*` keys, `DEBUG=False`, `ALLOWED_HOSTS` from `$ALLOWED_HOSTS` (default `.openmv.net,127.0.0.1`), `SECURE_PROXY_SSL_HEADER` + `CSRF_TRUSTED_ORIGINS` for Caddy.

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
- **Bind-mounted data dirs** (under `/home/deploy/openmv/repo/data/`):
  - `media/` — Django uploads served by Caddy and mounted into the container as `/app/media`.
  - `static/` — `collectstatic` output, mounted as `/app/static`. Re-populated by the `web` container's startup command.
  - `public/` — host the small files Apache used to alias (`robots.txt`, `favicon.ico`, `blender-efficiency.xlsx`).
- **`.env`** is **bind-mounted** into the container (`./.env:/app/.env:ro`) so `openmv/settings/base.py` finds it on import. Settings now read process env first, so an alternative is to drop the bind-mount and set the same keys in `web.environment` directly — but the bind-mount is currently the simpler path because it keeps the `POSTGRES_*` / `SQL_*` / `SECRET_KEY` config in one place. Never commit `.env`.
- **`DJANGO_SETTINGS_MODULE=openmv.settings.prod`** is set on the `web` service in `docker-compose.prod.yml`; this is what selects the prod-only DB / hosts / proxy headers. Don't rely on the `manage.py` default for production.
- **Caddy config**: `/etc/caddy/Caddyfile` on the host. Reload with `sudo systemctl reload caddy` (validate first with `sudo caddy validate --config /etc/caddy/Caddyfile`).
- **TLS**:
  - `openmv.net` and `www.openmv.net` use a **Cloudflare Origin Certificate** (15-year, signed by Cloudflare's internal CA) at `/etc/caddy/origin-certs/openmv.net/`. Cloudflare's edge serves a public-trusted cert to visitors and re-encrypts to origin in `Full (strict)` mode.
  - `test.openmv.net` uses Caddy-managed Let's Encrypt. It must stay **DNS-only** (grey cloud) in Cloudflare so the HTTP/TLS challenge can reach origin directly.
- **Auto-deploy**: every push to `master` fires `.github/workflows/deploy.yml`, which SSHes into Hetzner and triggers `bin/deploy-impl.sh`. The deploy script runs `docker compose -f docker-compose.prod.yml up -d --build` (which in turn runs `migrate --noinput` + `collectstatic --noinput` on container start, then boots gunicorn) and sanity-curls `127.0.0.1:8001`.
- **Manual deploy** (rollback, hotfix, debugging): from `/home/deploy/openmv/repo/`, run `git pull && docker compose -f docker-compose.prod.yml up -d --build` directly.
- **Public IPs**: IPv4 `178.104.167.195`, IPv6 `2a01:4f8:1c19:2380::1`. Behind Cloudflare's anycast for the apex; visible directly only for `test.openmv.net`.

## Gotchas worth knowing before editing

1. **`DatasetManager.get_queryset` filters out `is_hidden=True` rows from the public site _and_ from the admin list.** `Dataset.objects` is the only manager, so the admin's `DatasetAdmin` queryset is filtered too. To re-edit a hidden dataset, flip `is_hidden` directly in the DB (`./manage.py shell` or a `psql` session) — there is no `all_objects` escape hatch.
2. **`download_dataset` relies on the file URL being publicly reachable.** It returns `HttpResponseRedirect(file_obj.link_to_file.url)`. In production Caddy serves `/media/` directly from a bind-mounted host directory. Locally, `openmv/urls.py` wires `static(MEDIA_URL, document_root=MEDIA_ROOT)` under `DEBUG=True` so `runserver` serves uploads from `BASE_DIR/media/` (the `--nostatic` flag in `make debug` only suppresses the staticfiles app's auto-serving and does not affect those explicit URL patterns).
3. **`DataFile.link_to_file` values stored in the DB are `datasets/<file>.<ext>`** (no leading `media/`). Linode's legacy data had a `media/` prefix that was stripped during the Hetzner cutover. If you ever re-restore from a stale Linode dump, re-run: `UPDATE datasetapp_datafile SET link_to_file = regexp_replace(link_to_file, '^media/', '') WHERE link_to_file LIKE 'media/%';`
4. **`DataFile.objects.filter(...)[0]` in `download_dataset`** still uses `[0]` indexing inside a `try/except IndexError`. If you "tidy" it to `.first()`, preserve the same 404 path. (The two `Dataset.objects.filter(...)[0]` siblings have already been migrated to `.first()` + `None` check.)
5. **`special_message` is rendered with `|safe|escape`** in `all_datasets.html`. The chain is contradictory; `safe` wins. The string is set in the view (not user input), so it's not exploitable today, but don't add user-controlled content to it.
6. **The `datasetapp` logger is configured by the `LOGGING` dict in `openmv/settings/base.py`** and writes to stdout via a `StreamHandler`. In the production Docker container that means `docker logs` (and any host log shipper) captures everything; locally it streams to the `runserver` terminal. Override the level for ad-hoc debugging by setting `DATASETAPP_LOG_LEVEL=DEBUG` in `.env` or the process env.

## Tooling

- **Dependencies** are managed with [uv](https://docs.astral.sh/uv/). The source of truth is `pyproject.toml` + the committed `uv.lock`. There is no `requirements.txt`.
  - Install everything: `uv sync --dev`
  - Add a runtime dep: `uv add <pkg>`; dev dep: `uv add --dev <pkg>`
  - Refresh the lockfile after manual edits: `uv lock`
  - Django is pinned `>=4.2,<5.0` until 5.x has been smoke-tested on staging.
- **Tests** run with `uv run pytest` (or `make test`). `pytest-django` is wired through `[tool.pytest.ini_options]` in `pyproject.toml`. Smoke suite lives in `datasetapp/tests/test_views.py`.
- **GitHub Actions** runs `pre-commit run --all-files` and `pytest` on every PR and on push to `master` (`.github/workflows/ci.yml`). The pytest step injects `SECRET_KEY` directly via the workflow `env:` block — no `.env` file is created.
- **Docker compose**: `docker-compose.yml` is for **local development** (volume-mounts the source for hot reload, runs `runserver` against SQLite via `openmv.settings.dev`). `docker-compose.prod.yml` is the **production** compose used on Hetzner (bind-mounts `.env` and `data/` dirs, sets `DJANGO_SETTINGS_MODULE=openmv.settings.prod`, runs `migrate` + `collectstatic` + `gunicorn`, binds to loopback on offset ports `8001`/`5434`). Both use the same `Dockerfile`.
- **pre-commit** is configured (`.pre-commit-config.yaml`) — hooks are kept on current stable releases (`pre-commit-hooks` v5, `mypy` v1.13, `isort` 5.13, `black` 24.10, `blacken-docs` 1.19, `flake8` 7.1). Refresh with `pre-commit autoupdate` and re-run `pre-commit run --all-files` before merging.
- **flake8** config: `.flake8`. Line length 100. Ignores E266/E203/E231/W503.

## Branch conventions

- Production deploys ship from `master`.
- Modernization work happens on `claude/modernize-legacy-repo-*` branches and is reviewed before merge.

## Outstanding work

The GitHub issue tracker is the single source of truth for outstanding work: <https://github.com/kgdunn/Django-dataset-download-app/issues>. Don't duplicate the list here — it goes stale.

## Keeping this file consistent

CLAUDE.md must stay consistent with the codebase. On any PR that touches `datasetapp/`, `openmv/`, `pyproject.toml`, `Makefile`, `.pre-commit-config.yaml`, or `.github/workflows/`, re-read this file before opening the PR and update anything that has drifted — Project shape, How it runs, Gotchas, Tooling, Branch conventions. If you're Claude Code, run this consistency check on every implementation task, not just when explicitly asked.
