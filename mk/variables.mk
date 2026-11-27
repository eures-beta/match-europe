# Initialisation commune, avant toute expansion ou sous-commande.
unexport RUN REPO JOB PATTERN CONTEXT LINES REFRESH PR FILE
.DEFAULT_GOAL := help
export MATCH_PR_NUMBER := $(value PR)
PYTHON_VERSION := $(shell cat .python-version)
PYTHON_MINOR := $(word 1,$(subst ., ,$(PYTHON_VERSION))).$(word 2,$(subst ., ,$(PYTHON_VERSION)))
PYTHON_BOOTSTRAP ?= python$(PYTHON_MINOR)
ALBERT_INPUT ?=
ALBERT_OUTPUT ?= .runtime/albert-evaluation.json
JS_TESTS ?= $(shell find tests -type f \( -name '*.test.cjs' -o -name 'test_*.cjs' \) | LC_ALL=C sort)
QUALITY_PYTHON ?= .venv-quality/bin/python
PYTHON ?= .venv/bin/python
CATALOG_SOURCES ?= .runtime/catalog-sources
CATALOG_OUTPUT ?= .runtime/catalog-staging
CATALOG_DIR ?= eures_beta/occupations/data
CATALOG_REPORT ?= .runtime/catalog-validation.json
CATALOG_VERSION ?=
CATALOG_SOURCE_URL ?=
CATALOG_ALLOW_REMOVALS ?= 0
CATALOG_SYNC_OPTIONS = --output "$(CATALOG_OUTPUT)" $(if $(filter 1,$(CATALOG_ALLOW_REMOVALS)),--allow-removals,)
HOST ?= 127.0.0.1
PORT ?= 8000
TESTS ?= tests eures_beta.planning.tests
TEST_ARGS ?= --verbosity=0
SEED_ARGS ?=
LOAD_ENV = set -e; set -a; if [ -f .env ]; then . ./.env; fi; set +a;
MANAGE = $(LOAD_ENV) "$(PYTHON)" manage.py
EMAIL ?=
LANGUAGE ?= fr
INVITATION ?=
ORIGIN ?=
GITLEAKS ?= gitleaks
export SECURITY_ALERT_FILE := $(value FILE)
ci-status ci-errors: export CI_RUN = $(value RUN)
ci-status ci-errors: export CI_REPO = $(value REPO)
ci-status ci-errors: export CI_JOB = $(value JOB)
ci-status ci-errors: export CI_PATTERN = $(value PATTERN)
ci-status ci-errors: export CI_CONTEXT = $(value CONTEXT)
ci-status ci-errors: export CI_LINES = $(value LINES)
ci-status ci-errors: export CI_REFRESH = $(value REFRESH)
