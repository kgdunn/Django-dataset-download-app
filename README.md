# OpenMV.net Datasets

The Django site behind <https://openmv.net> — a public catalogue of small, real-world datasets used as worked examples in the textbook *[Process Improvement using Data](http://learnche.org/pid)* by Kevin Dunn.

The site lets visitors:

- Browse every public dataset in one sortable table.
- Filter datasets by tag.
- Read a per-dataset detail page with description, source, shape, usage restrictions, and contact info.
- Download a dataset in CSV / XLS / XML / MAT format. Each download is logged (IP, user-agent, referrer) for hit-counting.

## Layout

```
.
├── manage.py
├── Makefile                  # dev tasks (install, migrate, test, lint, debug, docker-up, ...)
├── pyproject.toml            # uv-managed dependencies + pytest config
├── uv.lock                   # committed lockfile
├── Dockerfile                # multi-stage image for local dev (and future prod)
├── docker-compose.yml        # web + postgres for local dev parity
├── .github/workflows/ci.yml  # pre-commit + pytest on push and PR
├── openmv/                   # Django project (settings, root URLs, WSGI/ASGI)
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
├── datasetapp/               # the only Django app
│   ├── models.py             # Tag, Dataset, DataFile, Hit
│   ├── views.py              # display_all, display_by_tag, about_dataset, download_dataset
│   ├── urls.py
│   ├── admin.py
│   ├── apps.py
│   ├── migrations/
│   ├── templates/datasetapp/ # base.html, all_datasets.html, dataset_info.html
│   └── templatetags/         # `slice_string` filter
├── .pre-commit-config.yaml
├── .flake8
├── .gitignore
├── .env.example              # copy to .env and fill in
├── README.md
├── CLAUDE.md                 # repo orientation + roadmap
└── LICENSE
```

## Requirements

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) for dependency management
- PostgreSQL (production / docker compose) — SQLite is used automatically when `DJANGO_DEBUG=1`.

Dependencies are declared in `pyproject.toml` and pinned in `uv.lock`.

## Local development

### Native (uv)

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd Django-dataset-download-app

# 2. Install dependencies into a managed venv
uv sync --dev

# 3. Configure environment
cp .env.example .env
# Edit .env: set SECRET_KEY to any random string, leave DJANGO_DEBUG=1.
# The Postgres-related keys are only consulted when DJANGO_DEBUG=0.

# 4. Run the dev server (collectstatic + migrate + createcachetable + runserver:8080)
make debug
```

### Docker compose

```bash
cp .env.example .env   # set SECRET_KEY and POSTGRES_*; set DJANGO_DEBUG=0
make docker-up         # builds + starts web (Django) and db (Postgres)
```

Either path serves <http://127.0.0.1:8080/>. Create a superuser with `uv run python manage.py createsuperuser` (native) or `docker compose exec web python manage.py createsuperuser` (Docker) to log into `/admin/` and add Tags / Datasets / DataFiles.

## Testing & CI

- `make test` — runs the smoke-test suite (`uv run pytest`).
- `make lint` — runs `pre-commit run --all-files`.
- `.github/workflows/ci.yml` runs both on every PR and on pushes to `master`.

## Production notes

- `DJANGO_DEBUG=0` switches the database to PostgreSQL using `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `SQL_HOST`, `SQL_PORT` from `.env`.
- `ALLOWED_HOSTS` is hardcoded to `.openmv.net` and `127.0.0.1` in `openmv/settings.py`. Change it there for other deployments.
- Static files land in `BASE_DIR / 'static'` after `python manage.py collectstatic`. Admin-uploaded dataset files land in `BASE_DIR / 'media'` (`MEDIA_ROOT`), reachable at `/media/` (`MEDIA_URL`). The live site has Apache serving `/static/` and `/media/` directly; the `download_dataset` view returns a 302 to the `/media/...` URL rather than streaming the file through Django. Locally, `runserver` serves `/media/` only when `DJANGO_DEBUG=1` (see `openmv/urls.py`); in production Apache must be configured to intercept `/media/` before the request reaches Django.
- The `Hit` table grows with every download. There is no automatic pruning.

## Tooling

- `make install` — `uv sync --dev`.
- `make migrate` — `uv run python manage.py migrate`.
- `make collectstatic` — `uv run python manage.py collectstatic --no-input`.
- `make test` — `uv run pytest`.
- `make lint` — `uv run pre-commit run --all-files`.
- `make debug` — collectstatic + migrate + createcachetable + runserver on `:8080`.
- `make docker-up` / `make docker-down` — wrappers over `docker compose`.
- `make clean` — remove `__pycache__`, caches, etc.

## License

BSD 3-Clause — see [LICENSE](LICENSE). © 2010–present Kevin Dunn.

## Contributing / roadmap

See [CLAUDE.md](CLAUDE.md) for an architectural overview and the prioritised list of future improvements.
