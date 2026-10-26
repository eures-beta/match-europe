#!/usr/bin/env bash
set -euo pipefail

# Un worker par défaut ; la configuration des environnements reste extérieure au code.
exec "${PYTHON:-python}" -m gunicorn config.wsgi:application \
    --bind "${GUNICORN_BIND:-0.0.0.0:9000}" \
    --workers "${WEB_CONCURRENCY:-1}" \
    --access-logfile - "$@"
