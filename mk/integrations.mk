.PHONY: albert-evaluate

albert-evaluate: ## Évaluer un texte local avec Albert (ALBERT_INPUT requis, appel réel explicite)
	@test -n "$(ALBERT_INPUT)" || { echo 'Indiquer ALBERT_INPUT.' >&2; exit 2; }
	@$(LOAD_ENV) "$(PYTHON)" manage.py evaluate_albert "$(ALBERT_INPUT)" --output "$(ALBERT_OUTPUT)"
