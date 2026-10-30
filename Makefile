# Développement local uniquement ; charger un .env personnel, jamais committé.
.DEFAULT_GOAL := help

# Prettier est un outil de développement ; aucune étape de build JavaScript.
.PHONY: install-js format-js format-js-check check-js
install-js: ## Installer la version verrouillée du formateur JavaScript
	npm ci --ignore-scripts --no-audit --no-fund

format-js: ## Formater les sources JavaScript (cible 100 colonnes, indentation 2 espaces)
	./node_modules/.bin/prettier --write 'eures_beta/**/*.{js,cjs,mjs}'

format-js-check: ## Vérifier le format JavaScript sans modifier les sources
	./node_modules/.bin/prettier --check 'eures_beta/**/*.{js,cjs,mjs}'

check-js: ## Vérifier la syntaxe de chaque source JavaScript
	./node_modules/.bin/prettier --debug-check 'eures_beta/**/*.{js,cjs,mjs}'
	find eures_beta -type f \( -name '*.js' -o -name '*.cjs' -o -name '*.mjs' \) -exec sh -c 'for file do node --check "$$file" || exit 1; done' sh {} +
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

.PHONY: format-html format-html-check translations-extract translations-check
PYTHON ?= .venv/bin/python
CATALOG_SOURCES ?= .runtime/catalog-sources
CATALOG_OUTPUT ?= .runtime/catalog-staging
CATALOG_DIR ?= eures_beta/occupations/data
CATALOG_REPORT ?= .runtime/catalog-validation.json

.PHONY: occupations-build occupations-validate occupations-test
occupations-build: ## Construire un catalogue en staging depuis les archives locales (sans réseau)
	$(PYTHON) -m eures_beta.occupations.tools.build_catalog --esco-dir "$(CATALOG_SOURCES)" --mapping "$(CATALOG_SOURCES)/esco-rome-other.csv" --rome "$(CATALOG_SOURCES)/rome-oct2026.xlsx" --output "$(CATALOG_OUTPUT)"

occupations-validate: ## Vérifier un catalogue et écrire son rapport, sans modifier les données
	@mkdir -p "$(dir $(CATALOG_REPORT))"
	$(PYTHON) -m eures_beta.occupations.tools.validate_catalog "$(CATALOG_DIR)" --report "$(CATALOG_REPORT)"

occupations-test: ## Tester uniquement le catalogue partagé et ses interfaces
	@$(LOAD_ENV) ME_DEMO_MODE=1 "$(PYTHON)" manage.py test eures_beta.occupations --noinput $(TEST_ARGS)

.PHONY: employer-test
employer-test: ## Tester le parcours employeur et sa recherche de métiers sur PostgreSQL
	@$(LOAD_ENV) ME_DEMO_MODE=1 "$(PYTHON)" manage.py test eures_beta.employers eures_beta.occupations eures_beta.test_employer_auth_translation eures_beta.test_employer_import_translation eures_beta.test_employer_landing_translation eures_beta.test_employer_privacy_translation --noinput $(TEST_ARGS)
HOST ?= 127.0.0.1
PORT ?= 8000
# Commandes usuelles sans paramètres ; chaque worktree possède son .venv et .env.
TEST_ARGS ?= --verbosity=0
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

.PHONY: employer-test
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

.PHONY: migrations-create
migrations-create: ## Générer les migrations locales à relire avant de les appliquer
	@$(MANAGE) makemigrations --noinput

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
.PHONY: translations-compile
translations-compile: ## Compiler les catalogues gettext après modification des fichiers .po
	@$(MANAGE) compilemessages

.PHONY: format-html format-html-check
format-html: ## Indenter les templates Django avec djLint (cible 120 colonnes)
	$(QUALITY_PYTHON) -m djlint eures_beta --reformat --quiet || test $$? -eq 1
format-html-check: ## Vérifier le formatage des templates sans les modifier
	$(QUALITY_PYTHON) -m djlint eures_beta --check
	$(QUALITY_PYTHON) -m eures_beta.template_layout
translations-extract: ## Actualiser les catalogues FR/DE depuis le code et les templates
	@$(MANAGE) makemessages --locale fr --locale de --no-wrap --no-obsolete --ignore build --ignore staticfiles --ignore '.venv*'

translations-check: ## Refuser les messages gettext non traduits ou encore marqués fuzzy
	$(PYTHON) -m eures_beta.translation_check
