# Développement local uniquement ; charger un .env personnel, jamais committé.
.DEFAULT_GOAL := help

# Docker limite réellement le serveur Linux ; aucun secret ni service distant.
.PHONY: e2e-test e2e-regression e2e-unit-test
e2e-unit-test: ## Vérifier le lecteur des e-mails capturés sans Docker ni envoi
	@$(MANAGE) test eures_beta.e2e.test_journeys --noinput

e2e-test: ## Tester les parcours HTTP sur Gunicorn/PostgreSQL, serveur plafonné à 256 Mio
	python3 -m eures_beta.e2e.run

e2e-regression: ## Vérifier que le même banc détecte l'OOM de l'ancien code avant #177
	python3 -m eures_beta.e2e.run --legacy-control

.PHONY: confirmations-migrations-test
confirmations-migrations-test: ## Vérifier l'upgrade de l'ancien schéma de confirmations sans perte
	@$(MANAGE) test eures_beta.matching.tests.test_confirmation_migration --noinput $(TEST_ARGS)

.PHONY: dialogue-run dialogue-test
.PHONY: dialogue-live-run dialogue-live-test dialogue-live-evaluate
dialogue-live-evaluate: ## Evaluer Albert réel sur six échanges fictifs, sans base ni données utilisateur
	@$(MANAGE) evaluate_dialogue_albert --live
dialogue-live-run: ## Essayer le raccordement Albert local sur 9045, données fictives uniquement
	@$(LOAD_ENV) CONFIRMATION_DIALOGUE_ENABLED=1 CONFIRMATION_DIALOGUE_SIMULATED=0 REQUEST_METRICS_ENABLED=0 MATCHING_ENABLED=1 TEST_ACCOUNTS_ENABLED=1 DJANGO_ENVIRONMENT=local EMAIL_DELIVERY_ENABLED=0 LOGIN_EMAIL_ENABLED=0 ALBERT_IMPORT_ENABLED=0 SKILLS_ALBERT_ENABLED=0 "$(PYTHON)" manage.py runserver 127.0.0.1:9045 --noreload
dialogue-live-test: ## Vérifier le raccordement avec API mockée, sans secret
	@$(MANAGE) test eures_beta.matching.tests.test_dialogue_albert --noinput $(TEST_ARGS)
dialogue-run: ## Essayer le dialogue Albert simulé local sur 9044, sans appel externe
	@$(LOAD_ENV) CONFIRMATION_DIALOGUE_SIMULATED=1 REQUEST_METRICS_ENABLED=0 MATCHING_ENABLED=1 TEST_ACCOUNTS_ENABLED=1 DJANGO_ENVIRONMENT=local EMAIL_DELIVERY_ENABLED=0 LOGIN_EMAIL_ENABLED=0 ALBERT_IMPORT_ENABLED=0 SKILLS_ALBERT_ENABLED=0 "$(PYTHON)" manage.py runserver 127.0.0.1:9044 --noreload
dialogue-test: ## Tester les propositions simulées et leur validation privée
	@$(MANAGE) test eures_beta.matching.tests.test_dialogue --noinput $(TEST_ARGS)

.PHONY: matching-format-html
matching-format-html: ## Formater uniquement le template du matching
	$(QUALITY_PYTHON) -m djlint eures_beta/matching/templates --reformat

.PHONY: matching-db-init matching-db-start matching-db-stop matching-seed matching-run matching-test matching-format matching-translations
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
matching-test: ## Tester le calcul, les décisions, les conflits et les droits d’accès
	@$(MANAGE) test eures_beta.matching --noinput $(TEST_ARGS)
matching-format: ## Formater uniquement le nouveau module de matching
	$(QUALITY_PYTHON) -m black --no-cache eures_beta/matching config/settings.py config/urls.py
matching-translations: ## Compiler les catalogues gettext sans modifier les traductions
	@$(MANAGE) compilemessages --locale fr --locale de --ignore ".venv*"

.PHONY: continuous-run continuous-test continuous-ui-test
.PHONY: continuous-source-prepare
continuous-source-prepare: ## Télécharger explicitement les trois exports publics ESCO épinglés et les vérifier
	@$(MANAGE) prepare_skill_source --download
continuous-ui-test: ## Tester l'affichage, les choix, les erreurs et réponses périmées sans navigateur
	node --test eures_beta/skills/tests/continuous.test.cjs
continuous-run: ## Tester toute la pile depuis l'accueil sur 9040, données fictives et Albert simulé
	@$(LOAD_ENV) CONTINUOUS_SKILLS_ENABLED=1 SKILLS_ALBERT_ENABLED=1 SKILLS_ALBERT_SIMULATED=1 ALBERT_IMPORT_ENABLED=1 ALBERT_API_KEY= DJANGO_ENVIRONMENT=local EMAIL_DELIVERY_ENABLED=0 LOGIN_EMAIL_ENABLED=0 TEST_ACCOUNTS_ENABLED=1 "$(PYTHON)" manage.py runserver "127.0.0.1:9040" --noreload

continuous-test: ## Vérifier les choix employeur/candidat, leur conservation et les protections locales
	@$(MANAGE) test eures_beta.skills.tests.test_continuous eures_beta.skills.tests.test_skill_source_prepare --noinput $(TEST_ARGS)

.PHONY: skills-albert-test skills-source-check skills-albert-ui-test
skills-albert-ui-test: continuous-ui-test ## Vérifier le composant intégré de compétences

skills-albert-test: ## Tester les suggestions, la réutilisation, les erreurs et droits sans Albert réel
	@$(MANAGE) test eures_beta.skills.tests.test_albert_skills --noinput $(TEST_ARGS)

skills-source-check: ## Vérifier hors ligne les archives officielles complètes avant la recette
	@$(MANAGE) check_skill_source

.PHONY: skills-pilot-test skills-pilot-build skills-pilot-audit
skills-pilot-audit: ## Comparer les 50 fiches aux archives ESCO épinglées, sans réseau ni base
	$(PYTHON) -m eures_beta.skills.tools.audit_skills_pilot --esco-dir "$(CATALOG_SOURCES)" --report .runtime/skills-pilot-audit.json

skills-pilot-build: ## Reconstruire le pilote depuis CATALOG_SOURCES en staging, sans réseau
	@$(MANAGE) sync_skills_pilot --esco-dir "$(CATALOG_SOURCES)" --output .runtime/skills-pilot-staging

skills-pilot-test: ## Vérifier le catalogue, les plafonds, les brouillons, les accès et les langues
	@$(MANAGE) test eures_beta.skills.tests.test_skills_pilot --noinput $(TEST_ARGS)

.PHONY: albert-test albert-run albert-evaluate
albert-test: ## Tester Albert sans réseau : validation, repli, droits et confidentialité
	@$(MANAGE) test eures_beta.employers.tests.test_albert eures_beta.integrations.tests.test_albert --noinput $(TEST_ARGS)

albert-run: ## Essayer le parcours Albert sur 9037, avec comptes fictifs et sans email réel
	@$(LOAD_ENV) ALBERT_IMPORT_ENABLED=1 TEST_ACCOUNTS_ENABLED=1 "$(PYTHON)" manage.py runserver "127.0.0.1:9037" --noreload

ALBERT_INPUT ?=
ALBERT_OUTPUT ?= .runtime/albert-evaluation.json
albert-evaluate: ## Évaluer un texte local avec Albert (ALBERT_INPUT requis, appel réel explicite)
	@test -n "$(ALBERT_INPUT)" || { echo 'Indiquer ALBERT_INPUT.' >&2; exit 2; }
	@$(LOAD_ENV) ALBERT_IMPORT_ENABLED=1 "$(PYTHON)" manage.py evaluate_albert "$(ALBERT_INPUT)" --output "$(ALBERT_OUTPUT)"

# Prettier est un outil de développement ; aucune étape de build JavaScript.
.PHONY: install-js format-js format-js-check check-js
install-js: ## Installer la version verrouillée du formateur JavaScript
	npm ci --ignore-scripts --no-audit --no-fund

format-js: ## Formater les sources JavaScript (cible 100 colonnes, indentation 2 espaces)
	./node_modules/.bin/prettier --write 'eures_beta/**/*.{js,cjs,mjs}'

format-js-check: ## Vérifier le format JavaScript sans modifier les sources
	./node_modules/.bin/prettier --check 'eures_beta/**/*.{js,cjs,mjs}'

check-js: ## Vérifier la syntaxe de chaque source JavaScript
	$(MAKE) admin-filter-test
	$(MAKE) candidate-ui-test
	$(MAKE) candidate-skills-ui-test
	./node_modules/.bin/prettier --debug-check 'eures_beta/**/*.{js,cjs,mjs}'
	find eures_beta -type f \( -name '*.js' -o -name '*.cjs' -o -name '*.mjs' \) -exec sh -c 'for file do node --check "$$file" || exit 1; done' sh {} +

# Même Prettier pour les CSS autonomes ; les ressources tierces restent intactes.
.PHONY: format-css format-css-check
format-css: ## Formater les feuilles CSS autonomes du projet avec Prettier
	./node_modules/.bin/prettier --write 'eures_beta/**/*.css'

format-css-check: ## Vérifier le format et la stabilité des CSS sans modifier les sources
	./node_modules/.bin/prettier --check 'eures_beta/**/*.css'
	./node_modules/.bin/prettier --debug-check 'eures_beta/**/*.css'

.PHONY: admin-filter-test
admin-filter-test: ## Tester le bouton des filtres admin et sa mémorisation, sans navigateur ni réseau
	node --test eures_beta/users/tests/admin_filters.test.cjs eures_beta/users/tests/admin_navigation.test.cjs
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

.PHONY: occupations-build occupations-validate occupations-test
.PHONY: occupations-performance-test
.PHONY: occupations-benchmark
.PHONY: occupations-memory-benchmark occupations-memory-test occupations-memory-serve
occupations-memory-serve: ## Servir localement avec un worker et huit threads pour vérifier la recherche (PORT=9048)
	@$(LOAD_ENV) "$(PYTHON)" -m gunicorn config.wsgi:application --bind "127.0.0.1:9048" --workers 1 --worker-class gthread --threads 8 --access-logfile -

occupations-memory-benchmark: ## Mesurer le pic mémoire du POST Django à froid, sans réseau ni base
	$(PYTHON) -m eures_beta.occupations.tools.benchmark_memory

occupations-memory-test: ## Vérifier le budget mémoire d’une recherche indépendante à froid
	@$(MANAGE) test eures_beta.occupations.tests.test_search_memory --noinput $(TEST_ARGS)

occupations-benchmark: ## Mesurer hors ligne le nettoyage et la recherche sur des intitulés fictifs (délai limité)
	$(PYTHON) -m eures_beta.occupations.tools.benchmark_search

occupations-performance-test: ## Vérifier que les intitulés mal formés ne bloquent pas la recherche (processus isolé)
	@$(MANAGE) test eures_beta.occupations.tests.test_search_performance --noinput $(TEST_ARGS)
occupations-build: ## Construire un catalogue en staging depuis les archives locales (sans réseau)
	$(PYTHON) -m eures_beta.occupations.tools.build_catalog --esco-dir "$(CATALOG_SOURCES)" --mapping "$(CATALOG_SOURCES)/esco-rome-other.csv" --rome "$(CATALOG_SOURCES)/rome-oct2026.xlsx" --output "$(CATALOG_OUTPUT)"

occupations-validate: ## Vérifier un catalogue et écrire son rapport, sans modifier les données
	@mkdir -p "$(dir $(CATALOG_REPORT))"
	$(PYTHON) -m eures_beta.occupations.tools.validate_catalog "$(CATALOG_DIR)" --report "$(CATALOG_REPORT)"

occupations-test: ## Tester uniquement le catalogue partagé et ses interfaces
	@$(LOAD_ENV) "$(PYTHON)" manage.py test eures_beta.occupations --noinput $(TEST_ARGS)

.PHONY: employer-test
employer-test: ## Tester le parcours employeur et sa recherche de métiers sur PostgreSQL
	@$(LOAD_ENV) "$(PYTHON)" manage.py test eures_beta.employers eures_beta.occupations eures_beta.test_employer_import_translation eures_beta.test_employer_landing_translation eures_beta.test_employer_privacy_translation --noinput $(TEST_ARGS)
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

test: ## Tests PostgreSQL : scénarios fictifs explicites et protections des parcours réels
	@$(LOAD_ENV) "$(PYTHON)" manage.py test eures_beta config --noinput $(TEST_ARGS)

.PHONY: employer-test
.PHONY: test-collection
test-collection: ## Vérifier les imports de tous les tests, sans créer de base
	@$(MANAGE) test config.test_test_collection --noinput

.PHONY: test-retired-paths
test-retired-paths: ## Vérifier le retrait des anciens parcours et les accès réels
	@$(MANAGE) test config.test_retired_paths --noinput

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

.PHONY: migrations-test
migrations-test: ## Tester les installations neuves et les transitions de migrations sur PostgreSQL local
	@$(LOAD_ENV) "$(PYTHON)" manage.py test eures_beta.employers.tests.test_autonomous_migrations eures_beta.employers.tests.test_model_renames --noinput $(TEST_ARGS)

.PHONY: permissions-sync permissions-test
.PHONY: admin-test
admin-test: ## Vérifier l'administration en lecture seule, ses droits et le masquage des secrets
	@$(MANAGE) test eures_beta.users.tests.test_readonly_admin --noinput $(TEST_ARGS)

permissions-sync: ## Réappliquer les groupes et droits administratifs versionnés à la base du .env
	@$(MANAGE) sync_group_and_perms

permissions-test: ## Tester la synchronisation et les protections de l'administration des comptes
	@$(MANAGE) test eures_beta.users.tests.test_permissions --noinput $(TEST_ARGS)


superuser: ## Créer un administrateur local, interactivement
	@$(MANAGE) createsuperuser

dbshell: ## Ouvrir psql sur la base locale configurée (SQL interactif)
	@$(MANAGE) dbshell

collectstatic: ## Collecter les statiques dans staticfiles/
	@$(MANAGE) collectstatic --noinput

.PHONY: install-test test-local serve db-create
install-test: ## Installer les dépendances pour les tests
	python3.14 -m venv .venv
	.venv/bin/python -m pip install -r requirements/test.txt

test-local: test ## Alias historique : tests via la configuration racine unique

serve: ## Tester le serveur WSGI sur loopback, avec un worker
	@$(LOAD_ENV) "$(PYTHON)" -m gunicorn config.wsgi:application --bind "127.0.0.1:$(PORT)" --workers 1

db-create: ## Créer une base PostgreSQL locale vide nommée PGDATABASE
	@$(LOAD_ENV) createdb --maintenance-db=postgres "$${PGDATABASE:?Renseigner PGDATABASE dans .env}"


.PHONY: test-navigation
.PHONY: landing-test
landing-test: ## Vérifier les trois pages d'entrée, leurs textes, langues et protections
	@$(LOAD_ENV) "$(PYTHON)" manage.py test eures_beta.test_home eures_beta.test_language_navigation eures_beta.test_employer_landing_translation eures_beta.test_public_positioning eures_beta.candidates.tests.test_landing --noinput $(TEST_ARGS)

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
	@$(MANAGE) compilemessages --ignore '.venv*'

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

.PHONY: journal-test
.PHONY: privacy-test
privacy-test: ## Vérifier la notice trilingue, les liens, les droits et l'absence de collecte
	@$(MANAGE) test eures_beta.test_data_protection --noinput $(TEST_ARGS)

journal-test: ## Vérifier le journal public trilingue, les liens et les méthodes HTTP
	@$(MANAGE) test eures_beta.test_journal eures_beta.test_public_navigation eures_beta.test_project --noinput $(TEST_ARGS)

.PHONY: users-upgrade-test
users-upgrade-test: ## Vérifier la migration des identités dans une base PostgreSQL locale jetable
	@$(LOAD_ENV) "$(PYTHON)" -m eures_beta.users.tools.verify_upgrade

.PHONY: registration-test
registration-test: ## Vérifier la fermeture de la création autonome de comptes
	@$(LOAD_ENV) "$(PYTHON)" manage.py test eures_beta.users.tests.test_closed_registration --noinput $(TEST_ARGS)

.PHONY: observability-test
observability-test: ## Vérifier les mesures de requêtes, la confidentialité et les diagnostics de timeout
	@$(LOAD_ENV) "$(PYTHON)" manage.py test eures_beta.observability --noinput $(TEST_ARGS)
.PHONY: login-test
.PHONY: test-accounts-seed test-accounts-test
test-accounts-seed: ## Ajouter les comptes et offres fictifs (local/preview explicitement activé uniquement)
	@$(MANAGE) seed_test_accounts

test-accounts-test: ## Vérifier les comptes fictifs, les changements de rôle et le verrouillage production
	@$(MANAGE) test eures_beta.users.tests.test_test_accounts --noinput $(TEST_ARGS)

.PHONY: invitations-test invitation-email
.PHONY: login-email
EMAIL ?=
LANGUAGE ?= fr
login-email: ## Simuler un email privé de connexion, sans envoi (EMAIL et ORIGIN requis)
	@test -n "$(EMAIL)" && test -n "$(ORIGIN)" || { echo 'Indiquer EMAIL et ORIGIN.' >&2; exit 2; }
	@$(MANAGE) login_email "$(EMAIL)" --origin "$(ORIGIN)" --language "$(LANGUAGE)"

invitations-test: ## Tester invitations, rôles, expiration et confirmation sur PostgreSQL local
	@$(MANAGE) test eures_beta.users.tests.test_invitations --noinput $(TEST_ARGS)

INVITATION ?=
ORIGIN ?=
invitation-email: ## Simuler un email privé contenant un lien secret (INVITATION=UUID et ORIGIN requis)
	@test -n "$(INVITATION)" && test -n "$(ORIGIN)" || { echo 'Indiquer INVITATION=UUID et ORIGIN=https://hote-autorise.' >&2; exit 2; }
	@$(MANAGE) invitation_email "$(INVITATION)" --origin "$(ORIGIN)"

login-test: ## Tester les liens magiques, sessions, limites et inscriptions fermées
	@$(LOAD_ENV) "$(PYTHON)" manage.py test eures_beta.users.tests --noinput $(TEST_ARGS)

.PHONY: user-kind-test
user-kind-test: ## Tester les rôles, la migration candidat et la fermeture des inscriptions
	@$(MANAGE) test eures_beta.users.tests.test_users eures_beta.users.tests.test_candidate_kind_migration eures_beta.users.tests.test_closed_registration --noinput $(TEST_ARGS)

.PHONY: candidate-run candidate-test
.PHONY: candidate-registration-run candidate-registration-test candidate-email candidate-registration-cleanup
candidate-registration-run: ## Démarrer le parcours candidat local sur 9035, sans email réel
	@$(MANAGE) runserver "127.0.0.1:9035"

candidate-registration-test: ## Tester la confirmation, les droits et la conservation des demandes candidat
	@$(MANAGE) test eures_beta.candidates.tests.test_registration --noinput $(TEST_ARGS)

candidate-email: ## Simuler un email de confirmation candidat (EMAIL et ORIGIN requis, lien privé)
	@test -n "$(EMAIL)" && test -n "$(ORIGIN)" || { echo 'Indiquer EMAIL et ORIGIN.' >&2; exit 2; }
	@$(MANAGE) candidate_email "$(EMAIL)" --origin "$(ORIGIN)"

candidate-registration-cleanup: ## Compter les demandes candidat expirées (CLEANUP_ARGS=--apply pour effacer)
	@$(MANAGE) cleanup_candidate_registrations $(CLEANUP_ARGS)

candidate-run: ## Démarrer le parcours candidat local sur le port 9031
	@$(MANAGE) runserver "127.0.0.1:9031"
candidate-test: ## Tester le questionnaire candidat sur PostgreSQL
	@$(LOAD_ENV) "$(PYTHON)" manage.py test eures_beta.candidates --noinput $(TEST_ARGS)

.PHONY: candidate-ui-test
candidate-ui-test: ## Vérifier la prolongation du brouillon candidat sans navigateur ni réseau
	node --test eures_beta/candidates/tests/journey_timeout.test.cjs

.PHONY: occupations-ui-test
occupations-ui-test: ## Tester la recherche métier du navigateur, ses erreurs et son délai limite
	node --test eures_beta/occupations/test_picker.cjs

.PHONY: employer-response-run employer-response-test
employer-response-run: ## Essayer les réponses employeur sur 9036, sans email réel
	@$(LOAD_ENV) TEST_ACCOUNTS_ENABLED=1 "$(PYTHON)" manage.py runserver "127.0.0.1:9036"

employer-response-test: ## Vérifier les réponses par compte, droits, conflits et traductions
	@$(MANAGE) test eures_beta.employers.tests.test_response_practice eures_beta.employers.tests.test_profile_rename --noinput $(TEST_ARGS)

.PHONY: environment-parity-test
environment-parity-test: ## Vérifier les parcours et droits dans les trois environnements, sans appel externe
	@$(MANAGE) test config.test_environment_parity eures_beta.emails.tests.test_backend eures_beta.employers.tests.test_albert eures_beta.skills.tests.test_skills_pilot eures_beta.skills.tests.test_albert_skills eures_beta.skills.tests.test_continuous eures_beta.skills.tests.test_skill_source_prepare eures_beta.matching --noinput $(TEST_ARGS)

.PHONY: candidate-skills-test candidate-skills-ui-test
candidate-skills-test: ## Tester le parcours sans métier, ses bornes, son stockage et ses droits
	@$(MANAGE) test eures_beta.candidates.tests.test_skill_project --noinput $(TEST_ARGS)

candidate-skills-ui-test: ## Tester la recherche, les étiquettes et les plafonds candidat sans réseau
	node --test eures_beta/candidates/tests/skill_selection.test.cjs


.PHONY: confirmations-test
confirmations-test: ## Tester les confirmations par offre et les accords distincts
	@$(MANAGE) test eures_beta.matching.tests.test_confirmations --noinput $(TEST_ARGS)

.PHONY: emails-test
emails-test: ## Vérifier le transport SMTP partagé et les protections sans envoi réel
	@$(MANAGE) test eures_beta.emails.tests --noinput $(TEST_ARGS)

.PHONY: adviser-invitations-test
adviser-invitations-test: ## Tester le tableau de bord conseiller et les invitations
	@$(MANAGE) test eures_beta.users.tests.test_adviser_invitations eures_beta.users.tests.test_invitations eures_beta.candidates.tests.test_registration --noinput $(TEST_ARGS)
