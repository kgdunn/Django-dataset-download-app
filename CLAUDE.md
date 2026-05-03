# CLAUDE.md

Orientation for Claude Code (and any other future maintainer) working in this repository. Keep this file up-to-date as the codebase evolves.

## What this repo is

The Django site behind <https://openmv.net> — a dataset catalogue that lists, describes, and serves downloads of small real-world datasets used in the textbook *Process Improvement using Data*. Originally written in 2010, ported to Python 3 / Django 3.2 in 2022, and currently in production.

**The live site cannot break.** Favour additive, behaviour-preserving changes. Anything that could change what visitors see should go through a staging deploy first.

## Project shape

- **Project**: `openmv/` (settings, URL conf, WSGI/ASGI).
- **App**: `datasetapp/` (the only app).
- **Models** (`datasetapp/models.py`): `Tag`, `Dataset`, `DataFile`, `Hit`.
  - `Dataset` ↔ `Tag` is many-to-many.
  - `Dataset` ↔ `DataFile` is one-to-many (a dataset can have CSV + XLS + XML + MAT siblings).
  - `Hit` records one download. Stores raw IP + UA + referrer.
- **Views** (`datasetapp/views.py`):
  - `display_all` — `/` — homepage table.
  - `display_by_tag` — `/tag/<slug>` — filter by tag.
  - `about_dataset` — `/info/<slug>` — detail page.
  - `download_dataset` — `/file/<name>.<ext>` — increments a `Hit` row, then 302-redirects to the media URL of the matching `DataFile`. The actual bytes are served by the front-end web server (Apache), not by Django.
- **Templates** (`datasetapp/templates/datasetapp/`):
  - `base.html` — Bootstrap 3 layout, inline `<style>`, no static-file dependency. Loads ECharts (CDN) for the detail-page sparkline.
  - `all_datasets.html` — the list page.
  - `dataset_info.html` — the detail page. Pulls in MathJax for any LaTeX in descriptions, renders a 365-day downloads sparkline (ECharts) below the download counter, an inline CSV preview table (first 10 rows) above the download block, and prev/next dataset links at the bottom.
- **Custom template tag**: `datasetapp/templatetags/extra_tags.py` defines a `slice_string` filter used in templates to trim filenames.
- **Admin**: registered in `datasetapp/admin.py` with `list_per_page = 2000` (deliberate — small dataset count).

## How it runs

- `make debug` runs `collectstatic --no-input`, `migrate`, `createcachetable`, then `runserver 8080 --nostatic`.
- Settings load `.env` via `python-dotenv`'s `dotenv_values()`. The file is **required** — `openmv/settings.py` asserts it exists on import.
- Database backend switches on `DJANGO_DEBUG`:
  - `1` → SQLite (`db.sqlite3` next to `manage.py`).
  - `0` → PostgreSQL using `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `SQL_HOST`, `SQL_PORT`.
- `ALLOWED_HOSTS = [".openmv.net", "127.0.0.1"]` is hardcoded in settings.

## Running locally

Two paths:

**Native (uv):**
```bash
cp .env.example .env   # edit SECRET_KEY; leave DJANGO_DEBUG=1 for SQLite
uv sync --dev
make debug             # collectstatic + migrate + createcachetable + runserver:8080
```

**Docker compose (with Postgres for parity with prod):**
```bash
cp .env.example .env   # set SECRET_KEY and the POSTGRES_* keys; set DJANGO_DEBUG=0
make docker-up         # docker compose up --build
```
Both paths serve <http://127.0.0.1:8080/>.

## Gotchas worth knowing before editing

1. **`DatasetManager.get_query_set` is dead code.** It uses the pre-Django-1.6 method name; the modern name is `get_queryset`. Right now `is_hidden=True` datasets are still rendered on the homepage. Renaming the method will make those rows disappear — verify with the site owner before flipping the switch.
2. **Hardcoded URL paths in templates.** `/info/{{slug}}`, `/file/{{name}}`, `/tag/{{name}}` are written as literals instead of `{% url %}` tags. URL changes have to be made in two places.
3. **`download_dataset` relies on the file URL being publicly reachable.** It returns `HttpResponseRedirect(file_obj.link_to_file.url)`. In production Apache serves `/media/`. Locally with `runserver --nostatic`, downloads will 404 unless you serve media manually.
4. **`Dataset.objects.filter(...)[0]`** is used in two views. If the queryset is empty it raises `IndexError`, which the surrounding `try/except IndexError` blocks catch — be careful not to "tidy" them away with `.first()` without preserving the same not-found path.
5. **`special_message` is rendered with `|safe|escape`** in `all_datasets.html`. The chain is contradictory; `safe` wins. The string is set in the view (not user input), so it's not exploitable today, but don't add user-controlled content to it.
6. **The logger writes to `<repo>/logfile.log`.** It's not in Django's `LOGGING` config; it's set up at module import time in `datasetapp/views.py`.

## Tooling

- **Dependencies** are managed with [uv](https://docs.astral.sh/uv/). The source of truth is `pyproject.toml` + the committed `uv.lock`. There is no `requirements.txt`.
  - Install everything: `uv sync --dev`
  - Add a runtime dep: `uv add <pkg>`; dev dep: `uv add --dev <pkg>`
  - Refresh the lockfile after manual edits: `uv lock`
  - Django is pinned `>=4.2,<5.0` until 5.x has been smoke-tested on staging.
- **Tests** run with `uv run pytest` (or `make test`). `pytest-django` is wired through `[tool.pytest.ini_options]` in `pyproject.toml`. Smoke suite lives in `datasetapp/tests/test_views.py`.
- **GitHub Actions** runs `pre-commit run --all-files` and `pytest` on every PR and on push to `master` (`.github/workflows/ci.yml`). The job synthesizes a stub `.env` because `openmv/settings.py` asserts one exists at import — see the "stop asserting `.env` exists" follow-up issue.
- **Docker compose** (`docker-compose.yml`) brings up `web` + `postgres` for **local development only**. Production still ships behind Apache; production-Docker is a tracked follow-up.
- **pre-commit** is configured (`.pre-commit-config.yaml`) but hook versions are pinned to late 2021 / early 2022. `pre-commit autoupdate` is a tracked follow-up.
- **flake8** config: `.flake8`. Line length 100. Ignores E266/E203/E231/W503.

## Branch conventions

- Production deploys ship from `master`.
- Modernization work happens on `claude/modernize-legacy-repo-*` branches and is reviewed before merge.

## Outstanding work

The GitHub issue tracker is the single source of truth for outstanding work: <https://github.com/kgdunn/Django-dataset-download-app/issues>. Don't duplicate the list here — it goes stale.

## Keeping this file consistent

CLAUDE.md must stay consistent with the codebase. On any PR that touches `datasetapp/`, `openmv/`, `pyproject.toml`, `Makefile`, `.pre-commit-config.yaml`, or `.github/workflows/`, re-read this file before opening the PR and update anything that has drifted — Project shape, How it runs, Gotchas, Tooling, Branch conventions. If you're Claude Code, run this consistency check on every implementation task, not just when explicitly asked.
