# Backup runbook

End-to-end operational guide for the openmv off-host backup. Read this
when you need to provision a new bucket, rotate credentials, restore from
backup, or take over backup ownership from a previous maintainer.

CLAUDE.md's `## Backups` section is the high-level orientation; this file
is the step-by-step runbook with exact commands.

## What gets backed up

The Hetzner-side script `bin/backup-openmv.sh` runs nightly under `deploy`
from cron and ships an off-host copy of the production stack to **AWS S3**.
Three things happen on every invocation:

1. **Postgres dump** of the running `db` container via
   `docker compose -f docker-compose.prod.yml exec -T db pg_dump --clean
   --if-exists`, gzipped, uploaded to
   `s3://$BACKUP_S3_BUCKET/$BACKUP_S3_PREFIX/db/daily/db_openmv-YYYY-MM-DD.sql.gz`.
   On the 1st of each month the same dump is also copied to
   `db/monthly/db_openmv-YYYY-MM.sql.gz`; on Jan 1 to
   `db/yearly/db_openmv-YYYY.sql.gz`.
2. **`aws s3 sync`** of `data/media/` and `data/public/` to the matching
   prefixes — without `--delete`, so an accidental local rm or detached
   bind-mount cannot propagate to the off-host copy. `data/static/` is
   intentionally **not** backed up because `collectstatic` regenerates it
   on every container start.
3. **Retention pruning** by S3 `LastModified`: `db/daily/` keeps the 15
   most recent objects, `db/monthly/` keeps 12, `db/yearly/` is never
   pruned.

S3 layout that results:

```
s3://$BACKUP_S3_BUCKET/$BACKUP_S3_PREFIX/
├── db/
│   ├── daily/    db_openmv-YYYY-MM-DD.sql.gz   (≤15)
│   ├── monthly/  db_openmv-YYYY-MM.sql.gz      (≤12)
│   └── yearly/   db_openmv-YYYY.sql.gz         (∞)
├── media/        mirror of data/media/
└── public/       mirror of data/public/
```

The destination is **deliberately AWS S3, not Hetzner Object Storage** —
keeping backups in a different cloud account from the production VPS so a
compromise of one doesn't reach the other.

## Prerequisites

Before starting:

- An AWS account that is **not** the same identity as Hetzner Cloud login.
- SSH access to the Hetzner VPS as `deploy`.
- The repo checked out at `/home/deploy/openmv/repo/` with the prod stack
  running (`docker compose -f docker-compose.prod.yml ps` shows `web` and
  `db` healthy).
- `.env` populated with the existing `POSTGRES_*` keys (already required
  by the prod stack).

## Part 1: AWS one-time setup

If `kgd-backups` already exists from the literature stack, skip 1a (the
bucket is shared). You still need a **new IAM user** with an
openmv-scoped policy in step 1b — never reuse literature's IAM
credentials.

### 1a. Bucket (skip if already created for literature)

S3 → Create bucket:

| Field                       | Value                                              |
| --------------------------- | -------------------------------------------------- |
| Bucket name                 | `kgd-backups` (must be globally unique; reuse the existing one if it already exists) |
| Region                      | `eu-central-1` (Frankfurt — close to Hetzner Nuremberg) |
| Block all public access     | Leave on (default)                                 |
| Bucket versioning           | **Enable** (guards against bad sync overwriting good data) |
| Default encryption          | SSE-S3 (`AES-256`) — confirm it's on (default since Jan 2023) |
| Object Lock                 | Off                                                |
| Tags                        | Optional, e.g. `project=openmv`                    |

### 1b. Create a dedicated IAM user with a tightly-scoped policy

IAM → Users → Create user:

- User name: `openmv-backup` (separate from `literature-backup`)
- **Do not** check "Provide user access to the AWS Management Console" —
  programmatic only.

After creation, on the user's **Permissions** tab, "Add permissions" →
"Attach policies directly" → "Create policy" (inline). Paste this,
replacing `kgd-backups` with your bucket name if different:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ListBucketUnderPrefix",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::kgd-backups",
      "Condition": {
        "StringLike": { "s3:prefix": ["openmv", "openmv/*"] }
      }
    },
    {
      "Sid": "ObjectsUnderPrefix",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::kgd-backups/openmv/*"
    }
  ]
}
```

Name it `openmv-backup-policy`. This grants exactly what the script needs
and nothing else: list under `openmv/`, read/write/delete objects under
`openmv/`. **No access to the `literature/` prefix in the same bucket**,
no IAM, no console.

### 1c. Generate access keys

IAM → Users → `openmv-backup` → Security credentials → Create access key:

- Use case: "Application running outside AWS"
- Copy the **Access key ID** and **Secret access key**. AWS shows the
  secret only once — if you miss it, delete the key and create a new one.

You'll paste both into Hetzner's `.env` in step 2b.

## Part 2: Hetzner one-time setup

SSH in as `deploy` (or `sudo -iu deploy`).

### 2a. Install the AWS CLI v2

If literature's backup is already running on this box, `aws` is already
installed — skip 2a. Otherwise:

Ubuntu 24.04 dropped the `awscli` apt package, so `sudo apt install
awscli` no longer works. Two supported alternatives — pick whichever
runs on your VPS.

**Preferred: snap.** Ships with Ubuntu Cloud images and tracks AWS CLI
v2 directly:

```bash
sudo snap install aws-cli --classic
aws --version          # expect: aws-cli/2.x.x ...
```

**Fallback: AWS's official zip installer.** Use this if snap isn't
available (rare on Hetzner Cloud Ubuntu images):

```bash
sudo apt install -y unzip curl
curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
unzip awscliv2.zip
sudo ./aws/install
aws --version
rm -rf awscliv2.zip aws
```

If `curl` rejects the URL with `URL rejected: Port number was not a
decimal number between 0 and 65535`, the paste turned a straight quote
into a curly one. Re-type the line by hand or use `wget -O awscliv2.zip
https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip` instead.

Don't use `pip install awscli` — that pulls v1, which is on its way out.

### 2b. Populate `.env`

```bash
cd /home/deploy/openmv/repo
git pull origin master           # ensure bin/backup-openmv.sh is present
nano .env                        # or your editor of choice
```

Append the five backup keys (paste real values from step 1c and your
chosen bucket name):

```dotenv
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=eu-central-1
BACKUP_S3_BUCKET=kgd-backups
BACKUP_S3_PREFIX=openmv
```

`POSTGRES_DB` and `POSTGRES_USER` already exist in `.env` from the prod
stack — the script reuses them. Never commit `.env`.

### 2c. Create the log directory

```bash
mkdir -p /home/deploy/openmv/backups
```

The cron line in step 2f writes its log there.

### 2d. Smoke-test by running once by hand

```bash
cd /home/deploy/openmv/repo
./bin/backup-openmv.sh
```

Expected output (timestamps will differ):

```
[backup-openmv] 2026-05-04T... starting; bucket=kgd-backups prefix=openmv
[backup-openmv] 2026-05-04T... db dumped: 12M
[backup-openmv] 2026-05-04T... uploaded daily dump
[backup-openmv] 2026-05-04T... media synced
[backup-openmv] 2026-05-04T... public synced
[backup-openmv] 2026-05-04T... prune db/daily/: 1 objects, nothing to remove
[backup-openmv] 2026-05-04T... prune db/monthly/: 0 objects, nothing to remove
[backup-openmv] 2026-05-04T... done
```

The first run uploads the **entire** `data/media/` tree — every dataset
file. On Hetzner's gigabit egress this should take a few minutes;
subsequent runs only re-upload changed files. If `data/media/` is large
(>1 GiB), schedule the first run at a quiet time.

### 2e. Verify in S3

From the same shell (or your laptop with `aws` configured against the
same access key, or the AWS console):

```bash
aws s3 ls s3://kgd-backups/openmv/db/daily/
aws s3 ls s3://kgd-backups/openmv/media/  | head
aws s3 ls s3://kgd-backups/openmv/public/
```

You should see today's `db_openmv-YYYY-MM-DD.sql.gz`, plus all the
dataset files mirrored under `media/`.

### 2f. Install the cron entry

As `deploy`:

```bash
crontab -e
```

Add exactly this line (it matches what CLAUDE.md documents):

```
35 21 * * *  /home/deploy/openmv/repo/bin/backup-openmv.sh >> /home/deploy/openmv/backups/backup.log 2>&1
```

That's 21:35 UTC nightly — the same slot the old Linode cron used.

Verify:

```bash
crontab -l
```

The script is **not** installed automatically by `bin/deploy-impl.sh`;
cron lives outside the repo because its presence and schedule are
operational state, not application state. If you migrate to a new VPS,
re-do this step.

## Part 3: Verifying nightly runs

After the first scheduled run (the next morning):

```bash
tail -n 20 /home/deploy/openmv/backups/backup.log
aws s3 ls s3://kgd-backups/openmv/db/daily/
```

You should see two `db_openmv-*.sql.gz` files (today's + yesterday's).
The 16th will start displacing the oldest, the 1st of next month will
deposit a `db/monthly/db_openmv-YYYY-MM.sql.gz`, and Jan 1 of next year
will drop a `db/yearly/db_openmv-YYYY.sql.gz`.

## Part 4: Restore drill (recommended within a week of setup)

Prove the path is genuinely restorable without touching prod. This
exercises the same commands you'd use in an actual recovery, but lands
the data in a throwaway container:

```bash
# Spin up an isolated Postgres
docker run --rm -d --name openmv-restore-test \
  -e POSTGRES_DB=openmv \
  -e POSTGRES_USER=openmv \
  -e POSTGRES_PASSWORD=test \
  postgres:16-alpine
sleep 5

# Pull the most recent daily and restore into it
aws s3 cp s3://kgd-backups/openmv/db/daily/db_openmv-$(date -u +%F).sql.gz - \
  | gunzip \
  | docker exec -i openmv-restore-test psql -U openmv -d openmv

# Sanity-check row counts against live
docker exec openmv-restore-test psql -U openmv -d openmv -c \
  "SELECT count(*) FROM datasetapp_dataset; SELECT count(*) FROM datasetapp_hit;"

docker rm -f openmv-restore-test
```

If the row counts match the live DB (within the day's `Hit` accrual),
the backup is restorable. Re-run this drill any time the schema changes
materially — `0002_drop_hit_pii` would be the kind of migration that
warrants a fresh drill.

## Real restore: full disaster recovery

If you ever need to restore prod from S3 (lost VPS, corrupted DB,
catastrophic admin error), the path is:

1. **Provision a fresh Hetzner VPS**, install Docker + Caddy, clone the
   repo to `/home/deploy/openmv/repo/`. Follow the *Production
   deployment (Hetzner)* section of CLAUDE.md.
2. **Re-do part 2** of this runbook on the new VPS (CLI install,
   `.env`, log dir).
3. **Pull the datasets back** before bringing the stack up:

   ```bash
   cd /home/deploy/openmv/repo
   aws s3 sync s3://kgd-backups/openmv/media/ data/media/
   aws s3 sync s3://kgd-backups/openmv/public/ data/public/
   ```

   `--delete` is deliberately omitted — if S3 has anything the local
   side lacks, copy it down; never the reverse.
4. **Bring the stack up** (Postgres starts empty):

   ```bash
   docker compose -f docker-compose.prod.yml up -d --build
   ```

5. **Restore the database** into the now-running `db` container. Pick
   the most recent useful snapshot — usually `db/daily/`, but if you're
   recovering from a longer-window incident, choose from `monthly/` or
   `yearly/` instead:

   ```bash
   aws s3 cp s3://kgd-backups/openmv/db/daily/db_openmv-YYYY-MM-DD.sql.gz - \
     | gunzip \
     | docker compose -f docker-compose.prod.yml exec -T db \
         psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"
   ```

   `pg_dump` was run with `--clean --if-exists`, so this restore
   wipes/recreates objects from the dump. Safe against a fresh DB; safe
   against an existing DB you want overwritten.
6. **Re-install the cron** (step 2f). Verify with `crontab -l`.
7. **Don't restore `data/static/`** — `collectstatic` regenerated it on
   container start in step 4. Restoring it would just be padding.
8. If the VPS is on a new IP, update Cloudflare DNS for `openmv.net` /
   `www.openmv.net` (and grey-cloud `test.openmv.net`).

## Troubleshooting

**`aws: command not found`** — re-run step 2a. The official installer
puts `aws` in `/usr/local/bin/`; make sure that's in `PATH` (it is by
default on Ubuntu 24.04).

**`Unable to locate credentials`** — the script sources `.env` via
`set -a; source .env; set +a`. Confirm `.env` contains `AWS_ACCESS_KEY_ID`
and `AWS_SECRET_ACCESS_KEY` and that the file is readable by `deploy`
(`ls -l /home/deploy/openmv/repo/.env`).

**`AccessDenied` on a `PutObject` / `s3 cp`** — the IAM policy in step 1b
must use the **exact** bucket name and prefix. A common mistake: writing
`kgd-backups/openmv` in the resource ARN where you should write
`kgd-backups/openmv/*` (the trailing `/*` is what permits objects
under the prefix, not the prefix itself).

**`pg_dump: error: connection to server failed`** — the `db` container
isn't healthy. Check `docker compose -f docker-compose.prod.yml ps` and
`docker compose -f docker-compose.prod.yml logs db`. The script runs
`pg_dump` *inside* the container via `docker compose exec`, so the
container's own credentials are what matter, not the host's.

**`aws s3 sync` reports no progress on the first run** — it really does
take a while on the first upload (every dataset file). Run with
`--cli-read-timeout 0 --no-progress` if you want quieter output, or just
let it finish.

**Pruning didn't remove anything I expected** — pruning is by S3
`LastModified`, not by filename date. If you re-upload an old key, it
becomes "newest" from S3's point of view. This is normally what you
want; just be aware.

**You rotate the IAM access key** — generate a new key in the AWS
console, update `.env` on the host, run `./bin/backup-openmv.sh` once by
hand to confirm the new key works, then deactivate (and after a day,
delete) the old key in IAM.

## References

- Script source: `bin/backup-openmv.sh`
- High-level overview: `CLAUDE.md` → *Backups* section
- Issue that drove this work: [#49](https://github.com/kgdunn/Django-dataset-download-app/issues/49)
- Release notes: `RELEASES.md` → *v1.4.0*
- AWS CLI install reference: <https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html>
