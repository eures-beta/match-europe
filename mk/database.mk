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
db-check: ## Vérifier la configuration PostgreSQL locale sans modification (rôle, CREATEDB, base)
	@$(LOAD_ENV) "$(PYTHON)" -m config.local_database check

db-create: ## Préparer la base locale du worktree si absente, sans créer de rôle
	@$(LOAD_ENV) "$(PYTHON)" -m config.local_database create
