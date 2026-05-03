# Releases

## v1.2.0

Django bumped from 4.2 LTS to 5.1, closing the E1 item on the modernization
roadmap (#42). Django 4.2 LTS is supported until April 2026; moving now gives
runway to catch any breakage before EOL.

### Highlights

- **Django 5.1** (#35): `pyproject.toml` pin moved from `>=4.2,<5.0` to
  `>=5.1,<5.2`; `uv.lock` refreshed (django 4.2.30 → 5.1.15). The smoke
  test suite (`datasetapp/tests/test_views.py`) passes unchanged against
  5.1; `manage.py check` and `manage.py check --deploy` report no new
  warnings beyond the pre-existing `SECURE_HSTS_PRELOAD=False` (deliberate
  staged HSTS rollout from C3). No code changes were needed — the
  pre-flight audit found no usage of the APIs Django 5.x removed
  (`USE_L10N`, `django.utils.timezone.utc`, `index_together`, etc.).
- **CLAUDE.md**: the "Tooling" section now reflects the new pin and notes
  the bump rationale; the "Outstanding work" referent (#35) is now closed.

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
