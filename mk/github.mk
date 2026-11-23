# Transmettre PR comme donnée, jamais comme fragment de commande shell.
.PHONY: pr-description
pr-description: ## Lire la description GitHub : make pr-description PR=195
	python3 -m config.pr_description
# Diagnostics GitHub en lecture seule ; pas de .env applicatif ni de shell imbriqué.
# Exporter les paramètres comme données évite de les interpoler dans la recette.
.PHONY: ci-status ci-errors
ci-status: ## Lire l'état des jobs GitHub Actions (RUN requis, REPO optionnel)
	python3 -m config.ci_diagnostics status

ci-errors: ## Lire les erreurs/arrêts CI avec cache local (RUN, JOB/PATTERN optionnels)
	python3 -m config.ci_diagnostics errors
