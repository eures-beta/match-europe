# One runtime declaration, also read by Clever Cloud and setup-python.

.PHONY: python-update-check python-update python-runtime-verify
python-runtime-verify: ## Vérifier l'interpréteur et sa maintenance hors réseau, avant installation
	$(PYTHON_BOOTSTRAP) -m config.python_runtime --verify
	$(PYTHON_BOOTSTRAP) -m unittest tests.config.test_python_runtime

python-update-check: ## Chercher une version Python stable et son image Docker, sans écrire
	python3 -m config.python_runtime

python-update: ## Mettre à jour la déclaration Python et son empreinte Docker (sans commit)
	python3 -m config.python_runtime --update

.PHONY: help install run test check migrate migrations superuser dbshell collectstatic

install: python-runtime-verify ## Installer les dépendances avec le Python déclaré dans .python-version
	$(PYTHON_BOOTSTRAP) -m venv .venv
	.venv/bin/python -m pip install -r requirements.txt

run: ## Démarrer Django avec le .env du worktree (PORT=8000, HOST=127.0.0.1)
	@$(MANAGE) runserver "$(HOST):$(PORT)"


collectstatic: ## Collecter les statiques dans staticfiles/
	@$(MANAGE) collectstatic --noinput

.PHONY: install-test serve db-check db-create
install-test: python-runtime-verify ## Installer les dépendances pour les tests
	$(PYTHON_BOOTSTRAP) -m venv .venv
	.venv/bin/python -m pip install -r requirements/test.txt

serve: ## Tester le serveur WSGI sur loopback, avec un worker
	@$(LOAD_ENV) "$(PYTHON)" -m gunicorn config.wsgi:application --bind "127.0.0.1:$(PORT)" --workers 1


.PHONY: clever-post-build clever-pre-run clever-run
clever-post-build: ## Reproduire la collecte des statiques du hook Clever
	@$(LOAD_ENV) PYTHON="$(PYTHON)" ./clevercloud/post_build.sh

clever-pre-run: ## Appliquer les migrations via le hook Clever sur la base du .env
	@$(LOAD_ENV) PYTHON="$(PYTHON)" ./clevercloud/pre_run.sh

clever-run: ## Tester le lancement Clever localement sur HOST:PORT (loopback par défaut)
	@$(LOAD_ENV) PYTHON="$(PYTHON)" GUNICORN_BIND="$(HOST):$(PORT)" ./clevercloud/run.sh
