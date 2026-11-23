# Docker limite réellement le serveur Linux ; aucun secret ni service distant.
.PHONY: e2e-test e2e-regression

e2e-test: ## Tester les parcours HTTP sur Gunicorn/PostgreSQL, serveur plafonné à 256 Mio
	$(PYTHON_BOOTSTRAP) -m tests.e2e.run

e2e-regression: ## Vérifier que le même banc détecte l'OOM de l'ancien code avant #177
	$(PYTHON_BOOTSTRAP) -m tests.e2e.run --legacy-control

# Tests JavaScript : un seul runner pour tous les fichiers, sans navigateur.
.PHONY: test-js
test-js: ## Tous les tests JavaScript ; JS_TESTS=chemin.test.cjs pour en sélectionner
	@test -n "$(strip $(JS_TESTS))" || { echo 'JS_TESTS ne doit pas être vide.' >&2; exit 2; }
	node --test $(JS_TESTS)

test: db-check ## Tests Django/PostgreSQL ; TESTS=module.Classe.methode, TEST_ARGS='-k motif'
	@test -n "$(strip $(TESTS))" || { echo 'TESTS ne doit pas être vide.' >&2; exit 2; }
	@$(MANAGE) test $(TESTS) --noinput $(TEST_ARGS)


.PHONY: users-upgrade-test
users-upgrade-test: ## Vérifier la migration des identités dans une base PostgreSQL locale jetable
	@$(LOAD_ENV) "$(PYTHON)" -m tests.users.verify_upgrade

.PHONY: test-accounts-seed
test-accounts-seed: ## Ajouter les comptes et offres fictifs (local/preview explicitement activé uniquement)
	@$(MANAGE) seed_test_accounts
