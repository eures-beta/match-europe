#!/usr/bin/env bash
set -euo pipefail

# Après installation des dépendances : préparer les ressources servies par WhiteNoise.
exec "${PYTHON:-python}" manage.py collectstatic --noinput
