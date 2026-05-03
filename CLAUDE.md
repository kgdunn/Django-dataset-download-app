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
  - `base.html` — Bootstrap 3 layout, inline `<style>`, no static-file dependency.
  - `all_datasets.html` — the list page.
  - `dataset_info.html` — the detail page; pulls in MathJax for any LaTeX in descriptions.
- **Custom template tag**: `datasetapp/templatetags/extra_tags.py` defines a `slice_string` filter used in templates to trim filenames.
- **Admin**: registered in `datasetapp/admin.py` with `list_per_page = 2000` (deliberate — small dataset count).

## How it runs

- `make debug` runs `collectstatic --no-input`, `migrate`, `createcachetable`, then `runserver 8080 --nostatic`.
- Settings load `.env` via `python-dotenv`'s `dotenv_values()`. The file is **required** — `openmv/settings.py` asserts it exists on import.
- Database backend switches on `DJANGO_DEBUG`:
  - `1` → SQLite (`db.sqlite3` next to `manage.py`).
  - `0` → PostgreSQL using `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `SQL_HOST`, `SQL_PORT`.
- `ALLOWED_HOSTS = [".openmv.net", "127.0.0.1"]` is hardcoded in settings.

## Gotchas worth knowing before editing

1. **`DatasetManager.get_query_set` is dead code.** It uses the pre-Django-1.6 method name; the modern name is `get_queryset`. Right now `is_hidden=True` datasets are still rendered on the homepage. Renaming the method will make those rows disappear — verify with the site owner before flipping the switch.
2. **Hardcoded URL paths in templates.** `/info/{{slug}}`, `/file/{{name}}`, `/tag/{{name}}` are written as literals instead of `{% url %}` tags. URL changes have to be made in two places.
3. **`download_dataset` relies on the file URL being publicly reachable.** It returns `HttpResponseRedirect(file_obj.link_to_file.url)`. In production Apache serves `/media/`. Locally with `runserver --nostatic`, downloads will 404 unless you serve media manually.
4. **`Dataset.objects.filter(...)[0]`** is used in two views. If the queryset is empty it raises `IndexError`, which the surrounding `try/except IndexError` blocks catch — be careful not to "tidy" them away with `.first()` without preserving the same not-found path.
5. **Broken `%`-format string** at `datasetapp/views.py:73`: `log_file.error("An invalid dataset was requested" % dataset_name.lower())`. The format string has no `%s` placeholder, so this raises `TypeError` if it ever runs. Treat it as a latent bug.
6. **`special_message` is rendered with `|safe|escape`** in `all_datasets.html`. The chain is contradictory; `safe` wins. The string is set in the view (not user input), so it's not exploitable today, but don't add user-controlled content to it.
7. **The logger writes to `<repo>/logfile.log`.** It's not in Django's `LOGGING` config; it's set up at module import time in `datasetapp/views.py`.

## Tooling

- `pre-commit` is configured (`.pre-commit-config.yaml`) but pinned to versions from late 2021 / early 2022. Hook upgrades are listed in the TODO below.
- `pytest` is in `requirements.txt` but there are no tests yet.
- `flake8` config: `.flake8`. Line length 100. Ignores E266/E203/E231/W503.
- `requirements.txt` is unpinned. The only floor is `django>4.0`.

## Branch conventions

- Production deploys ship from `master`.
- Modernization work happens on `claude/modernize-legacy-repo-*` branches and is reviewed before merge.

## Future improvements (TODO)

Roughly ordered by safety × value. Pick from the top.

### Safety net (do before touching production behaviour)

- [ ] **Pin `requirements.txt`** to currently-resolved versions (`pip freeze`). Add an upper bound on Django (`django>=4.2,<5.0`) until 5.x has been smoke-tested on a staging copy.
- [ ] **Add a `.python-version`** (or `python_requires` in a `pyproject.toml`) capturing Python 3.11.
- [ ] **Add a smoke-test `pytest` suite**: `/` returns 200, `/info/<known-slug>` returns 200, `/file/<known-file>` returns 302 to the expected URL, missing slugs return 404 / redirect cleanly. `pytest` is already in the requirements.
- [ ] **Add a GitHub Actions CI workflow** that runs `pre-commit run --all-files` and `pytest` on push and on PR.

### Latent bugs (small, well-scoped)

- [ ] **Fix `DatasetManager.get_query_set` → `get_queryset`** in `datasetapp/models.py:18-21`. Verify with the site owner which `is_hidden=True` datasets currently leak onto the homepage; some may need to be unhidden before the rename.
- [ ] **Fix the broken `%`-format log call** in `datasetapp/views.py:73` (`"An invalid dataset was requested" % dataset_name.lower()`).
- [ ] **Replace `Dataset.objects.filter(slug=…)[0]`** in `about_dataset` and `download_dataset` with `.first()` plus an explicit `None` check, while preserving the existing 404 / redirect behaviour.
- [ ] **Replace hardcoded `/info/`, `/file/`, `/tag/` paths in templates** with `{% url 'datasetapp:dataset-about-a-dataset' dataset.slug %}` etc.

### Tooling refresh (dev-only, low blast radius)

- [ ] **Update `.pre-commit-config.yaml`** to current hook versions: `pre-commit-hooks` v4.5+, `black` 24.x, `isort` 5.13+, `flake8` 7.x, `mypy` 1.x, `blacken-docs` 1.16+. Run `pre-commit autoupdate`.
- [ ] **Drop `conda` from `Makefile`**; use plain `python -m pip install`. Drop the `--use-deprecated=legacy-resolver` flag (gone in pip 24).
- [ ] **Add `make collectstatic`, `make migrate`, `make test`** as separate targets so CI / deploy scripts can call them directly.
- [ ] **Add an `.editorconfig`** so editors agree on indentation and line endings.

### Settings, deployment, security

- [ ] **Split `openmv/settings.py`** into `settings/base.py`, `settings/dev.py`, `settings/prod.py`; pick via `DJANGO_SETTINGS_MODULE`.
- [ ] **Stop asserting `.env` exists**; read from `os.environ` first and fall back to a dotenv file. This unblocks containerized hosts that inject env vars directly. Consider switching from `python-dotenv` to `django-environ` or `environs`.
- [ ] **Move `ALLOWED_HOSTS` into the environment** so non-`openmv.net` deploys (staging, preview) don't need a code change.
- [ ] **Add production security headers** in `settings/prod.py`: `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_PROXY_SSL_HEADER`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `CSRF_TRUSTED_ORIGINS=['https://openmv.net','https://www.openmv.net']`. Roll out behind the existing reverse proxy and verify before merging.
- [ ] **Configure `MEDIA_URL` / `MEDIA_ROOT` explicitly** so `runserver` can serve media in development. Document the production handoff to Apache.
- [ ] **Configure `DATABASES['default']['CONN_MAX_AGE']`** for PostgreSQL connection reuse.
- [ ] **Add a Django `LOGGING` dict** and remove the ad-hoc `RotatingFileHandler` that `datasetapp/views.py` configures at import time.
- [ ] **Add `whitenoise`** for static file serving so deployments don't need Apache config to ship CSS.

### Bigger projects

- [ ] **Upgrade Bootstrap 3 → 5** with template rewrites (class names change: `well`, grid columns, navbar, etc.). Schedule alongside a visual redesign.
- [ ] **Migrate to Django 5.x** once the test suite is in place.
- [ ] **Add a `Dockerfile` + `docker-compose.yml`** with a Postgres service for reproducible local dev.
- [ ] **Tag a `v1.0.0` release** so production rollbacks have a target.
- [ ] **GDPR / privacy review of the `Hit` table.** It currently stores raw IPs and full UA strings forever. Options: truncate IPs (`/24` for IPv4, `/64` for IPv6), add a retention policy / cron-based pruning, or replace with a counter that doesn't keep PII.
- [ ] **Add Next/Previous dataset links on the detail page** (already noted as a TODO inside `views.py` and `dataset_info.html`).
- [ ] **Show a preview of the first N rows** on the dataset detail page (also noted as a long-standing TODO in `views.py`).
