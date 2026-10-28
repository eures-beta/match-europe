# Développement local uniquement ; charger un .env personnel, jamais committé.
.DEFAULT_GOAL := help
# Outillage isolé des dépendances de l'application et des identifiants personnels.
QUALITY_PYTHON ?= .venv-quality/bin/python

.PHONY: install-quality format format-check
install-quality: ## Installer Black dans un environnement dédié (Python 3.14)
	python3.14 -m venv .venv-quality
	.venv-quality/bin/python -m pip install -r requirements/quality.txt

format: ## Formater les fichiers Python avec Black (modifie les fichiers)
	$(QUALITY_PYTHON) -m black --no-cache .

format-check: ## Vérifier le formatage sans modifier les fichiers
	$(QUALITY_PYTHON) -m black --check --diff --no-cache .
PYTHON ?= .venv/bin/python
HOST ?= 127.0.0.1
PORT ?= 8000
TEST_ARGS ?=
# .env est un fichier shell : ne pas l'inclure comme syntaxe Make (secrets avec $).
LOAD_ENV = set -e; set -a; if [ -f .env ]; then . ./.env; fi; set +a;
MANAGE = $(LOAD_ENV) "$(PYTHON)" manage.py

.PHONY: help install run test check migrate migrations superuser dbshell collectstatic
help: ## Afficher les commandes et paramètres usuels
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z_-]+:.*## / {printf "  %-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@printf '\nParamètres : PYTHON, HOST, PORT, TEST_ARGS (ex. --parallel 2).\n'

install: ## Installer les dépendances dans .venv (Python 3.14 requis)
	python3.14 -m venv .venv
	.venv/bin/python -m pip install -r requirements.txt

run: ## Démarrer le serveur local, http://127.0.0.1:8000/
	@$(MANAGE) runserver "$(HOST):$(PORT)"

test: ## Tests PostgreSQL : scénarios fictifs explicites et contrôles hors démo
	@$(LOAD_ENV) ME_DEMO_MODE=1 "$(PYTHON)" manage.py test eures_beta config --noinput $(TEST_ARGS)

.PHONY: test-collection
test-collection: ## Vérifier les imports de tous les tests, sans créer de base
	@$(MANAGE) test config.test_test_collection --noinput

.PHONY: test-demo-modes
test-demo-modes: ## Vérifier les réglages réels et les protections hors démo
	@$(MANAGE) test config.test_demo_modes --noinput

check: ## Vérifier Django et l'absence de migrations oubliées
	@$(MANAGE) check
	@$(MANAGE) makemigrations --check --dry-run

migrate: ## Appliquer les migrations à la base sélectionnée par .env
	@$(MANAGE) migrate

migrations: ## Afficher l'état des migrations sans les appliquer
	@$(MANAGE) showmigrations

superuser: ## Créer un administrateur local, interactivement
	@$(MANAGE) createsuperuser

dbshell: ## Ouvrir psql sur la base locale configurée (SQL interactif)
	@$(MANAGE) dbshell

collectstatic: ## Collecter les statiques dans staticfiles/
	@$(MANAGE) collectstatic --noinput

.PHONY: install-test test-local seed-demo serve db-create
install-test: ## Installer aussi les dépendances du diagnostic Push pour les tests
	python3.14 -m venv .venv
	.venv/bin/python -m pip install -r requirements/test.txt

test-local: test ## Alias historique : tests via la configuration racine unique

seed-demo: ## Initialiser les rôles fictifs manuellement (développement local)
	@$(MANAGE) seed_demo

serve: ## Tester le serveur WSGI sur loopback, avec un worker
	@$(LOAD_ENV) "$(PYTHON)" -m gunicorn config.wsgi:application --bind "127.0.0.1:$(PORT)" --workers 1

db-create: ## Créer une base PostgreSQL locale vide nommée PGDATABASE
	@$(LOAD_ENV) createdb --maintenance-db=postgres "$${PGDATABASE:?Renseigner PGDATABASE dans .env}"

.PHONY: employer-pages-build
employer-pages-build: ## Générer les pages historiques dans build/employer-ui (jamais les templates actifs)
	node scripts/employer-ui/build.cjs
	node scripts/employer-ui/build-import.cjs
	node scripts/employer-ui/build-candidate.cjs

.PHONY: test-navigation
test-navigation: ## Vérifier la bascule de langue et les liens ouverts avant un déploiement
	@$(MANAGE) test eures_beta.test_language_navigation --noinput $(TEST_ARGS)

.PHONY: clever-post-build clever-pre-run clever-run
clever-post-build: ## Reproduire la collecte des statiques du hook Clever
	@$(LOAD_ENV) PYTHON="$(PYTHON)" ./clevercloud/post_build.sh

clever-pre-run: ## Appliquer les migrations via le hook Clever sur la base du .env
	@$(LOAD_ENV) PYTHON="$(PYTHON)" ./clevercloud/pre_run.sh

clever-run: ## Tester le lancement Clever localement sur HOST:PORT (loopback par défaut)
	@$(LOAD_ENV) PYTHON="$(PYTHON)" GUNICORN_BIND="$(HOST):$(PORT)" ./clevercloud/run.sh
