# Développement local uniquement ; charger un .env personnel, jamais committé.
.DEFAULT_GOAL := help

# Docker limite réellement le serveur Linux ; aucun secret ni service distant.
.PHONY: e2e-test e2e-regression

e2e-test: ## Tester les parcours HTTP sur Gunicorn/PostgreSQL, serveur plafonné à 256 Mio
	python3 -m eures_beta.e2e.run

e2e-regression: ## Vérifier que le même banc détecte l'OOM de l'ancien code avant #177
	python3 -m eures_beta.e2e.run --legacy-control

.PHONY: dialogue-run
.PHONY: dialogue-live-run dialogue-live-evaluate
dialogue-live-evaluate: ## Evaluer Albert réel sur six échanges fictifs, sans base ni données utilisateur
	@$(MANAGE) evaluate_dialogue_albert --live
dialogue-live-run: ## Essayer le raccordement Albert local sur 9045, données fictives uniquement
	@$(LOAD_ENV) CONFIRMATION_DIALOGUE_ENABLED=1 CONFIRMATION_DIALOGUE_SIMULATED=0 REQUEST_METRICS_ENABLED=0 MATCHING_ENABLED=1 TEST_ACCOUNTS_ENABLED=1 DJANGO_ENVIRONMENT=local EMAIL_DELIVERY_ENABLED=0 LOGIN_EMAIL_ENABLED=0 ALBERT_IMPORT_ENABLED=0 SKILLS_ALBERT_ENABLED=0 "$(PYTHON)" manage.py runserver 127.0.0.1:9045 --noreload
dialogue-run: ## Essayer le dialogue Albert simulé local sur 9044, sans appel externe
	@$(LOAD_ENV) CONFIRMATION_DIALOGUE_SIMULATED=1 REQUEST_METRICS_ENABLED=0 MATCHING_ENABLED=1 TEST_ACCOUNTS_ENABLED=1 DJANGO_ENVIRONMENT=local EMAIL_DELIVERY_ENABLED=0 LOGIN_EMAIL_ENABLED=0 ALBERT_IMPORT_ENABLED=0 SKILLS_ALBERT_ENABLED=0 "$(PYTHON)" manage.py runserver 127.0.0.1:9044 --noreload

.PHONY: matching-format-html
matching-format-html: ## Formater uniquement le template du matching
	$(QUALITY_PYTHON) -m djlint eures_beta/matching/templates --reformat

.PHONY: matching-db-init matching-db-start matching-db-stop matching-seed matching-run matching-format matching-translations
matching-db-init: ## Initialiser PostgreSQL isolé pour la recette matching (port 55441)
	@mkdir -p .runtime
	initdb -D .runtime/matching-pg -U matching_local --auth-local=trust --auth-host=trust
matching-db-start: ## Démarrer le PostgreSQL de recette sur loopback uniquement
	pg_ctl -D .runtime/matching-pg -l .runtime/matching-pg.log -o "-h 127.0.0.1 -p 55441 -k /tmp" start
matching-db-stop: ## Arrêter uniquement le PostgreSQL de cette recette
	pg_ctl -D .runtime/matching-pg stop
matching-seed: ## Ajouter les scénarios fictifs de matching sans écraser les profils
	@$(MANAGE) seed_matching_trial
matching-run: ## Essayer le matching sur 9041, sans email ni Albert réel
	@$(LOAD_ENV) MATCHING_ENABLED=1 DJANGO_ENVIRONMENT=local EMAIL_DELIVERY_ENABLED=0 LOGIN_EMAIL_ENABLED=0 ALBERT_IMPORT_ENABLED=0 SKILLS_ALBERT_ENABLED=0 "$(PYTHON)" manage.py runserver 127.0.0.1:9041 --noreload
matching-format: ## Formater uniquement le nouveau module de matching
	$(QUALITY_PYTHON) -m black --no-cache eures_beta/matching config/settings.py config/urls.py
matching-translations: ## Compiler les catalogues gettext sans modifier les traductions
	@$(MANAGE) compilemessages --locale fr --locale de --ignore ".venv*"

.PHONY: continuous-run
.PHONY: continuous-source-prepare
continuous-source-prepare: ## Télécharger explicitement les trois exports publics ESCO épinglés et les vérifier
	@$(MANAGE) prepare_skill_source --download
continuous-run: ## Tester toute la pile depuis l'accueil sur 9040, données fictives et Albert simulé
	@$(LOAD_ENV) CONTINUOUS_SKILLS_ENABLED=1 SKILLS_ALBERT_ENABLED=1 SKILLS_ALBERT_SIMULATED=1 ALBERT_IMPORT_ENABLED=1 ALBERT_API_KEY= DJANGO_ENVIRONMENT=local EMAIL_DELIVERY_ENABLED=0 LOGIN_EMAIL_ENABLED=0 TEST_ACCOUNTS_ENABLED=1 "$(PYTHON)" manage.py runserver "127.0.0.1:9040" --noreload

.PHONY: skills-source-check

skills-source-check: ## Vérifier hors ligne les archives officielles complètes avant la recette
	@$(MANAGE) check_skill_source

.PHONY: skills-pilot-build skills-pilot-audit
skills-pilot-audit: ## Comparer les 50 fiches aux archives ESCO épinglées, sans réseau ni base
	$(PYTHON) -m eures_beta.skills.tools.audit_skills_pilot --esco-dir "$(CATALOG_SOURCES)" --report .runtime/skills-pilot-audit.json

skills-pilot-build: ## Reconstruire le pilote depuis CATALOG_SOURCES en staging, sans réseau
	@$(MANAGE) sync_skills_pilot --esco-dir "$(CATALOG_SOURCES)" --output .runtime/skills-pilot-staging

.PHONY: albert-run albert-evaluate

albert-run: ## Essayer le parcours Albert sur 9037, avec comptes fictifs et sans email réel
	@$(LOAD_ENV) ALBERT_IMPORT_ENABLED=1 TEST_ACCOUNTS_ENABLED=1 "$(PYTHON)" manage.py runserver "127.0.0.1:9037" --noreload

ALBERT_INPUT ?=
ALBERT_OUTPUT ?= .runtime/albert-evaluation.json
albert-evaluate: ## Évaluer un texte local avec Albert (ALBERT_INPUT requis, appel réel explicite)
	@test -n "$(ALBERT_INPUT)" || { echo 'Indiquer ALBERT_INPUT.' >&2; exit 2; }
	@$(LOAD_ENV) ALBERT_IMPORT_ENABLED=1 "$(PYTHON)" manage.py evaluate_albert "$(ALBERT_INPUT)" --output "$(ALBERT_OUTPUT)"

# Tests JavaScript : un seul runner pour tous les fichiers, sans navigateur.
JS_TESTS ?= $(shell find eures_beta -type f \( -name '*.test.cjs' -o -name 'test_*.cjs' \) | LC_ALL=C sort)
.PHONY: test-js
test-js: ## Tous les tests JavaScript ; JS_TESTS=chemin.test.cjs pour en sélectionner
	@test -n "$(strip $(JS_TESTS))" || { echo 'JS_TESTS ne doit pas être vide.' >&2; exit 2; }
	node --test $(JS_TESTS)

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

# Même Prettier pour les CSS autonomes ; les ressources tierces restent intactes.
.PHONY: format-css format-css-check
format-css: ## Formater les feuilles CSS autonomes du projet avec Prettier
	./node_modules/.bin/prettier --write 'eures_beta/**/*.css'

format-css-check: ## Vérifier le format et la stabilité des CSS sans modifier les sources
	./node_modules/.bin/prettier --check 'eures_beta/**/*.css'
	./node_modules/.bin/prettier --debug-check 'eures_beta/**/*.css'

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
CATALOG_VERSION ?=
CATALOG_SOURCE_URL ?=
CATALOG_ALLOW_REMOVALS ?= 0
CATALOG_SYNC_OPTIONS = --output "$(CATALOG_OUTPUT)" $(if $(filter 1,$(CATALOG_ALLOW_REMOVALS)),--allow-removals,)

.PHONY: occupations-sync-esco occupations-sync-rome occupations-sync-esco-rome occupations-promote
occupations-promote: ## Valider le staging et remplacer explicitement les quatre JSON versionnés et le manifeste
	$(PYTHON) -m eures_beta.occupations.tools.promote_catalog --source "$(CATALOG_OUTPUT)" --target "$(CATALOG_DIR)"

occupations-sync-esco: ## Télécharger les métiers ESCO FR/EN/DE et préparer les JSON en staging
	@$(MANAGE) sync_esco $(CATALOG_SYNC_OPTIONS) $(if $(CATALOG_VERSION),--source-version "$(CATALOG_VERSION)",)

occupations-sync-rome: ## Préparer ensemble ROME et OGR depuis une édition XLSX officielle
	@$(MANAGE) sync_rome $(CATALOG_SYNC_OPTIONS) $(if $(CATALOG_VERSION),--source-version "$(CATALOG_VERSION)",) $(if $(CATALOG_SOURCE_URL),--source-url "$(CATALOG_SOURCE_URL)",)

occupations-sync-esco-rome: ## Préparer les correspondances officielles ESCO/ROME
	@$(MANAGE) sync_esco_rome $(CATALOG_SYNC_OPTIONS) $(if $(CATALOG_SOURCE_URL),--source-url "$(CATALOG_SOURCE_URL)",)

.PHONY: occupations-build occupations-validate
.PHONY: occupations-benchmark
.PHONY: occupations-memory-benchmark occupations-memory-serve
occupations-memory-serve: ## Servir localement avec un worker et huit threads pour vérifier la recherche (PORT=9048)
	@$(LOAD_ENV) "$(PYTHON)" -m gunicorn config.wsgi:application --bind "127.0.0.1:9048" --workers 1 --worker-class gthread --threads 8 --access-logfile -

occupations-memory-benchmark: ## Mesurer le pic mémoire du POST Django à froid, sans réseau ni base
	$(PYTHON) -m eures_beta.occupations.tools.benchmark_memory

occupations-benchmark: ## Mesurer hors ligne le nettoyage et la recherche sur des intitulés fictifs (délai limité)
	$(PYTHON) -m eures_beta.occupations.tools.benchmark_search

occupations-build: ## Construire un catalogue en staging depuis les archives locales (sans réseau)
	$(PYTHON) -m eures_beta.occupations.tools.build_catalog --esco-dir "$(CATALOG_SOURCES)" --mapping "$(CATALOG_SOURCES)/esco-rome-other.csv" --rome "$(CATALOG_SOURCES)/rome-oct2026.xlsx" --output "$(CATALOG_OUTPUT)"

occupations-validate: ## Vérifier un catalogue et écrire son rapport, sans modifier les données
	@mkdir -p "$(dir $(CATALOG_REPORT))"
	$(PYTHON) -m eures_beta.occupations.tools.validate_catalog "$(CATALOG_DIR)" --report "$(CATALOG_REPORT)"

HOST ?= 127.0.0.1
PORT ?= 8000
# Commandes usuelles sans paramètres ; chaque worktree possède son .venv et .env.
TESTS ?= eures_beta config
TEST_ARGS ?= --verbosity=0
# .env est un fichier shell : ne pas l'inclure comme syntaxe Make (secrets avec $).
LOAD_ENV = set -e; set -a; if [ -f .env ]; then . ./.env; fi; set +a;
MANAGE = $(LOAD_ENV) "$(PYTHON)" manage.py

.PHONY: help install run test check migrate migrations superuser dbshell collectstatic
help: ## Afficher les commandes et paramètres usuels
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@printf '\nParamètres : PYTHON, HOST, PORT, TESTS, TEST_ARGS, JS_TESTS.\n'

install: ## Installer les dépendances dans .venv (Python 3.14 requis)
	python3.14 -m venv .venv
	.venv/bin/python -m pip install -r requirements.txt

run: ## Démarrer le serveur local, http://127.0.0.1:8000/
	@$(MANAGE) runserver "$(HOST):$(PORT)"

test: ## Tests Django/PostgreSQL ; TESTS=module.Classe.methode, TEST_ARGS='-k motif'
	@test -n "$(strip $(TESTS))" || { echo 'TESTS ne doit pas être vide.' >&2; exit 2; }
	@$(MANAGE) test $(TESTS) --noinput $(TEST_ARGS)

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

.PHONY: permissions-sync

permissions-sync: ## Réappliquer les groupes et droits administratifs versionnés à la base du .env
	@$(MANAGE) sync_group_and_perms

superuser: ## Créer un administrateur local, interactivement
	@$(MANAGE) createsuperuser

dbshell: ## Ouvrir psql sur la base locale configurée (SQL interactif)
	@$(MANAGE) dbshell

collectstatic: ## Collecter les statiques dans staticfiles/
	@$(MANAGE) collectstatic --noinput

.PHONY: install-test serve db-create
install-test: ## Installer les dépendances pour les tests
	python3.14 -m venv .venv
	.venv/bin/python -m pip install -r requirements/test.txt

serve: ## Tester le serveur WSGI sur loopback, avec un worker
	@$(LOAD_ENV) "$(PYTHON)" -m gunicorn config.wsgi:application --bind "127.0.0.1:$(PORT)" --workers 1

db-create: ## Créer une base PostgreSQL locale vide nommée PGDATABASE
	@$(LOAD_ENV) createdb --maintenance-db=postgres "$${PGDATABASE:?Renseigner PGDATABASE dans .env}"

.PHONY: clever-post-build clever-pre-run clever-run
clever-post-build: ## Reproduire la collecte des statiques du hook Clever
	@$(LOAD_ENV) PYTHON="$(PYTHON)" ./clevercloud/post_build.sh

clever-pre-run: ## Appliquer les migrations via le hook Clever sur la base du .env
	@$(LOAD_ENV) PYTHON="$(PYTHON)" ./clevercloud/pre_run.sh

clever-run: ## Tester le lancement Clever localement sur HOST:PORT (loopback par défaut)
	@$(LOAD_ENV) PYTHON="$(PYTHON)" GUNICORN_BIND="$(HOST):$(PORT)" ./clevercloud/run.sh
.PHONY: translations-compile
translations-compile: ## Compiler les catalogues gettext après modification des fichiers .po
	@$(MANAGE) compilemessages --ignore '.venv*'

.PHONY: format-html format-html-check
format-html: ## Indenter les templates Django avec djLint (cible 120 colonnes)
	$(QUALITY_PYTHON) -m djlint eures_beta --reformat --quiet || test $$? -eq 1
format-html-check: ## Vérifier le formatage des templates sans les modifier
	$(QUALITY_PYTHON) -m djlint eures_beta --check
	$(QUALITY_PYTHON) -m eures_beta.template_layout
translations-extract: ## Actualiser les catalogues FR/DE depuis le code et les templates
	@$(MANAGE) makemessages --locale fr --locale de --extension html,txt,py,subject --no-wrap --no-obsolete --ignore build --ignore staticfiles --ignore '.venv*'

translations-check: ## Refuser les messages gettext non traduits ou encore marqués fuzzy
	$(PYTHON) -m eures_beta.translation_check

.PHONY: users-upgrade-test
users-upgrade-test: ## Vérifier la migration des identités dans une base PostgreSQL locale jetable
	@$(LOAD_ENV) "$(PYTHON)" -m eures_beta.users.tools.verify_upgrade

.PHONY: test-accounts-seed
test-accounts-seed: ## Ajouter les comptes et offres fictifs (local/preview explicitement activé uniquement)
	@$(MANAGE) seed_test_accounts

.PHONY: invitation-email
.PHONY: login-email
EMAIL ?=
LANGUAGE ?= fr
login-email: ## Simuler un email privé de connexion, sans envoi (EMAIL et ORIGIN requis)
	@test -n "$(EMAIL)" && test -n "$(ORIGIN)" || { echo 'Indiquer EMAIL et ORIGIN.' >&2; exit 2; }
	@$(MANAGE) login_email "$(EMAIL)" --origin "$(ORIGIN)" --language "$(LANGUAGE)"

INVITATION ?=
ORIGIN ?=
invitation-email: ## Simuler un email privé contenant un lien secret (INVITATION=UUID et ORIGIN requis)
	@test -n "$(INVITATION)" && test -n "$(ORIGIN)" || { echo 'Indiquer INVITATION=UUID et ORIGIN=https://hote-autorise.' >&2; exit 2; }
	@$(MANAGE) invitation_email "$(INVITATION)" --origin "$(ORIGIN)"

.PHONY: candidate-run
.PHONY: candidate-registration-run candidate-email candidate-registration-cleanup
candidate-registration-run: ## Démarrer le parcours candidat local sur 9035, sans email réel
	@$(MANAGE) runserver "127.0.0.1:9035"

candidate-email: ## Simuler un email de confirmation candidat (EMAIL et ORIGIN requis, lien privé)
	@test -n "$(EMAIL)" && test -n "$(ORIGIN)" || { echo 'Indiquer EMAIL et ORIGIN.' >&2; exit 2; }
	@$(MANAGE) candidate_email "$(EMAIL)" --origin "$(ORIGIN)"

candidate-registration-cleanup: ## Compter les demandes candidat expirées (CLEANUP_ARGS=--apply pour effacer)
	@$(MANAGE) cleanup_candidate_registrations $(CLEANUP_ARGS)

candidate-run: ## Démarrer le parcours candidat local sur le port 9031
	@$(MANAGE) runserver "127.0.0.1:9031"

.PHONY: employer-response-run
employer-response-run: ## Essayer les réponses employeur sur 9036, sans email réel
	@$(LOAD_ENV) TEST_ACCOUNTS_ENABLED=1 "$(PYTHON)" manage.py runserver "127.0.0.1:9036"
