#!/usr/bin/env bash
set -euo pipefail

# Avant chaque démarrage : appliquer les migrations de la base liée à l'application.
exec "${PYTHON:-python}" manage.py migrate --noinput
