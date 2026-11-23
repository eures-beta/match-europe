.PHONY: help
help: ## Afficher les commandes et paramètres usuels
	@awk 'BEGIN {FS = ":.*## "} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-16s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@printf '\nParamètres : PYTHON, HOST, PORT, TESTS, TEST_ARGS, JS_TESTS.\n'
