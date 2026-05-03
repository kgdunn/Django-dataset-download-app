#!/bin/bash
# Production deploy implementation for Hetzner. Invoked by the wrapper at
# /home/deploy/openmv/bin/deploy.sh after that wrapper has fast-forwarded the
# repo to origin/master. Living here keeps the actual deploy steps under
# version control and reviewable in PRs.
#
# Run via the wrapper, not directly. The wrapper is the entry point baked
# into the SSH deploy key's authorized_keys forced command.

set -euo pipefail

cd "$(dirname "$0")/.."

echo "[deploy-impl] $(date -u +%FT%TZ) starting; HEAD=$(git rev-parse --short HEAD)"

docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps

# Give the web container a few seconds to run migrate + collectstatic and
# bind to 8000 inside the container, then sanity-check it's responding.
for i in 1 2 3 4 5 6 7 8 9 10; do
    if curl -sSf -o /dev/null --max-time 5 http://127.0.0.1:8001/; then
        echo "[deploy-impl] web responding on 127.0.0.1:8001"
        echo "[deploy-impl] $(date -u +%FT%TZ) done"
        exit 0
    fi
    sleep 2
done

echo "[deploy-impl] web did not respond on 127.0.0.1:8001 within 20s"
docker compose -f docker-compose.prod.yml logs --tail=40 web
exit 1
