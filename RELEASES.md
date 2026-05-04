# Releases

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
