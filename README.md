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
├── Makefile                  # one-shot dev tasks (debug, clean)
├── requirements.txt
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
- PostgreSQL (production) — SQLite is used automatically when `DJANGO_DEBUG=1`.
- The Python packages listed in `requirements.txt` (Django ≥ 4.0, `psycopg2-binary`, `python-dotenv`, plus dev tools).

## Local development

```bash
# 1. Clone and enter the repo
git clone <repo-url> && cd Django-dataset-download-app

# 2. Create a virtualenv and install dependencies
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env: set SECRET_KEY to any random string, leave DJANGO_DEBUG=1.
# The Postgres-related keys are only consulted when DJANGO_DEBUG=0.

# 4. Run the dev server (collectstatic + migrate + createcachetable + runserver:8080)
make debug
```

Visit <http://127.0.0.1:8080/>. Create a superuser with `python manage.py createsuperuser` to log into `/admin/` and add Tags / Datasets / DataFiles.

## Production notes

- `DJANGO_DEBUG=0` switches the database to PostgreSQL using `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `SQL_HOST`, `SQL_PORT` from `.env`.
- `ALLOWED_HOSTS` is hardcoded to `.openmv.net` and `127.0.0.1` in `openmv/settings.py`. Change it there for other deployments.
- Static files land in `BASE_DIR / 'static'` after `python manage.py collectstatic`. The live site has Apache serving `/static/` and `/media/` directly; the `download_dataset` view returns a redirect to the file URL rather than streaming the file through Django.
- The `Hit` table grows with every download. There is no automatic pruning.

## Tooling

- `make debug` — collectstatic + migrate + createcachetable + runserver on `:8080`.
- `make clean` — remove `__pycache__`, caches, and reinstall dev dependencies.
- `pre-commit run --all-files` — black, isort, flake8, mypy, plus a few hygiene checks. The pinned hook versions are old; see `CLAUDE.md` for the upgrade plan.

## License

BSD 3-Clause — see [LICENSE](LICENSE). © 2010–present Kevin Dunn.

## Contributing / roadmap

See [CLAUDE.md](CLAUDE.md) for an architectural overview and the prioritised list of future improvements.
