#!/bin/bash
# Off-host backup of openmv to AWS S3.
#
# Runs on the Hetzner host as the `deploy` user. Three responsibilities:
#
#   1. Postgres dump (pg_dump --clean --if-exists, gzipped) of the running
#      `db` container, uploaded to:
#        s3://$BACKUP_S3_BUCKET/$BACKUP_S3_PREFIX/db/daily/db_openmv-YYYY-MM-DD.sql.gz
#      On the 1st of each month the same dump is also copied to
#        .../db/monthly/db_openmv-YYYY-MM.sql.gz
#      and on Jan 1 to
#        .../db/yearly/db_openmv-YYYY.sql.gz
#
#   2. `aws s3 sync` of the bind-mounted dataset dirs (data/media/ and
#      data/public/) to the matching S3 prefixes. No --delete: an accidental
#      local rm or detached bind-mount must NOT propagate to the off-host
#      copy. data/static/ is intentionally skipped — collectstatic regenerates
#      it on every container start, so it has nothing worth preserving.
#
#   3. Retention pruning: db/daily/ keeps the 15 most recent objects,
#      db/monthly/ keeps the 12 most recent. db/yearly/ is never pruned.
#      Pruning is by S3 LastModified (not by filename parsing).
#
# Required env (sourced from the same .env the prod stack uses):
#   AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
#   BACKUP_S3_BUCKET                  e.g. openmv-backups
#   BACKUP_S3_PREFIX                  optional, defaults to "openmv"
#   POSTGRES_DB, POSTGRES_USER        already present for the prod stack
#
# Cron entry (deploy user, intentionally not auto-installed by deploy):
#   35 21 * * *  /home/deploy/openmv/repo/bin/backup-openmv.sh \
#       >> /home/deploy/openmv/backups/backup.log 2>&1

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

if [[ -f .env ]]; then
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
fi

: "${BACKUP_S3_BUCKET:?BACKUP_S3_BUCKET must be set (in .env or environment)}"
: "${POSTGRES_DB:?POSTGRES_DB must be set}"
: "${POSTGRES_USER:?POSTGRES_USER must be set}"
BACKUP_S3_PREFIX="${BACKUP_S3_PREFIX:-openmv}"

DATE_DAILY="$(date -u +%F)"
DATE_MONTH="$(date -u +%Y-%m)"
DATE_YEAR="$(date -u +%Y)"
DAY_OF_MONTH="$(date -u +%d)"
MONTH_OF_YEAR="$(date -u +%m)"

S3_BASE="s3://${BACKUP_S3_BUCKET}/${BACKUP_S3_PREFIX}"
COMPOSE="docker compose -f docker-compose.prod.yml"

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

DB_FILE="$TMP_DIR/db_openmv-${DATE_DAILY}.sql.gz"

log() {
    echo "[backup-openmv] $(date -u +%FT%TZ) $*"
}

log "starting; bucket=${BACKUP_S3_BUCKET} prefix=${BACKUP_S3_PREFIX}"

# 1. Postgres dump from the running container.
$COMPOSE exec -T db \
    pg_dump --no-owner --no-acl --clean --if-exists -Fp \
    -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    | gzip -9 > "$DB_FILE"
log "db dumped: $(du -h "$DB_FILE" | cut -f1)"

# 2. Upload to db/daily/, then promote to monthly/yearly when due.
aws s3 cp "$DB_FILE" "${S3_BASE}/db/daily/$(basename "$DB_FILE")"
log "uploaded daily dump"

if [[ "$DAY_OF_MONTH" == "01" ]]; then
    aws s3 cp \
        "${S3_BASE}/db/daily/$(basename "$DB_FILE")" \
        "${S3_BASE}/db/monthly/db_openmv-${DATE_MONTH}.sql.gz"
    log "promoted to monthly: db_openmv-${DATE_MONTH}.sql.gz"
fi

if [[ "$MONTH_OF_YEAR" == "01" && "$DAY_OF_MONTH" == "01" ]]; then
    aws s3 cp \
        "${S3_BASE}/db/daily/$(basename "$DB_FILE")" \
        "${S3_BASE}/db/yearly/db_openmv-${DATE_YEAR}.sql.gz"
    log "promoted to yearly: db_openmv-${DATE_YEAR}.sql.gz"
fi

# 3. Mirror datasets and small public files. No --delete (see header).
aws s3 sync data/media "${S3_BASE}/media/"
log "media synced"
aws s3 sync data/public "${S3_BASE}/public/"
log "public synced"

# 4. Prune oldest entries past the retention horizon.
prune_prefix() {
    local prefix="$1"
    local keep="$2"
    mapfile -t keys < <(
        aws s3api list-objects-v2 \
            --bucket "$BACKUP_S3_BUCKET" \
            --prefix "${BACKUP_S3_PREFIX}/${prefix}" \
            --query 'reverse(sort_by(Contents,&LastModified))[].Key' \
            --output text 2>/dev/null \
            | tr '\t' '\n'
    )
    local total=${#keys[@]}
    if (( total <= keep )); then
        log "prune ${prefix}: ${total} objects, nothing to remove"
        return
    fi
    local removed=0
    for key in "${keys[@]:keep}"; do
        [[ -z "$key" || "$key" == "None" ]] && continue
        aws s3 rm "s3://${BACKUP_S3_BUCKET}/${key}"
        removed=$((removed + 1))
    done
    log "prune ${prefix}: kept ${keep}, removed ${removed}"
}

prune_prefix "db/daily/" 15
prune_prefix "db/monthly/" 12
# db/yearly/ deliberately never pruned.

log "done"
