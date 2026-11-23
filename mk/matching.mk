.PHONY: dialogue-live-evaluate
dialogue-live-evaluate: ## Evaluer Albert réel sur six échanges fictifs, sans base ni données utilisateur
	@$(MANAGE) evaluate_dialogue_albert --live

.PHONY: matching-format-html
matching-format-html: ## Formater uniquement le template du matching
	$(QUALITY_PYTHON) -m djlint eures_beta/matching/templates --reformat

.PHONY: matching-db-init matching-db-start matching-db-stop matching-seed matching-format matching-translations
matching-db-init: ## Initialiser PostgreSQL isolé pour la recette matching (port 55441)
	@mkdir -p .runtime
	initdb -D .runtime/matching-pg -U matching_local --auth-local=trust --auth-host=trust
matching-db-start: ## Démarrer le PostgreSQL de recette sur loopback uniquement
	pg_ctl -D .runtime/matching-pg -l .runtime/matching-pg.log -o "-h 127.0.0.1 -p 55441 -k /tmp" start
matching-db-stop: ## Arrêter uniquement le PostgreSQL de cette recette
	pg_ctl -D .runtime/matching-pg stop
matching-seed: ## Ajouter les scénarios fictifs de matching sans écraser les profils
	@$(MANAGE) seed_matching_trial
matching-format: ## Formater uniquement le nouveau module de matching
	$(QUALITY_PYTHON) -m black --no-cache eures_beta/matching config/settings.py config/urls.py
matching-translations: ## Compiler les catalogues gettext sans modifier les traductions
	@$(MANAGE) compilemessages --locale fr --locale de --ignore ".venv*"
