# Prettier est un outil de développement ; aucune étape de build JavaScript.
.PHONY: install-js format-js format-js-check check-js
install-js: ## Installer la version verrouillée du formateur JavaScript
	npm ci --ignore-scripts --no-audit --no-fund

format-js: ## Formater les sources JavaScript (cible 100 colonnes, indentation 2 espaces)
	./node_modules/.bin/prettier --write 'eures_beta/**/*.{js,cjs,mjs}' 'tests/**/*.{js,cjs,mjs}' '.github/*.cjs'

format-js-check: ## Vérifier le format JavaScript sans modifier les sources
	./node_modules/.bin/prettier --check 'eures_beta/**/*.{js,cjs,mjs}' 'tests/**/*.{js,cjs,mjs}' '.github/*.cjs'

check-js: ## Vérifier la syntaxe de chaque source JavaScript
	./node_modules/.bin/prettier --debug-check 'eures_beta/**/*.{js,cjs,mjs}' 'tests/**/*.{js,cjs,mjs}' '.github/*.cjs'
	find eures_beta tests .github -type f \( -name '*.js' -o -name '*.cjs' -o -name '*.mjs' \) -exec sh -c 'for file do node --check "$$file" || exit 1; done' sh {} +

# Même Prettier pour les CSS autonomes ; les ressources tierces restent intactes.
.PHONY: format-css format-css-check
format-css: ## Formater les feuilles CSS autonomes du projet avec Prettier
	./node_modules/.bin/prettier --write 'eures_beta/**/*.css'

format-css-check: ## Vérifier le format et la stabilité des CSS sans modifier les sources
	./node_modules/.bin/prettier --check 'eures_beta/**/*.css'
	./node_modules/.bin/prettier --debug-check 'eures_beta/**/*.css'

# Outillage isolé des dépendances de l'application et des identifiants personnels.

.PHONY: install-quality format format-check
install-quality: python-runtime-verify ## Installer Black avec le Python déclaré dans .python-version
	$(PYTHON_BOOTSTRAP) -m venv .venv-quality
	.venv-quality/bin/python -m pip install -r requirements/quality.txt

format: ## Formater les fichiers Python avec Black (modifie les fichiers)
	$(QUALITY_PYTHON) -m black --no-cache .

format-check: ## Vérifier le formatage sans modifier les fichiers
	$(QUALITY_PYTHON) -m black --check --diff --no-cache .

.PHONY: format-html format-html-check translations-extract translations-check
check: docs-check ## Vérifier les budgets documentaires, Django et les migrations
	@$(MANAGE) check
	@$(MANAGE) makemigrations --check --dry-run

.PHONY: docs-check
docs-check: ## Vérifier les tailles des consignes, skills et documents de reprise (sans base)
	python3 -m config.documentation

.PHONY: format-html format-html-check
format-html: ## Indenter les templates Django avec djLint (cible 120 colonnes)
	$(QUALITY_PYTHON) -m djlint eures_beta --reformat --quiet || test $$? -eq 1
format-html-check: ## Vérifier le formatage des templates sans les modifier
	$(QUALITY_PYTHON) -m djlint eures_beta --check
	$(QUALITY_PYTHON) -m eures_beta.template_layout
	$(QUALITY_PYTHON) -m djlint eures_beta --lint --configuration .djlint-css.json --rules .djlint_rules.yaml
	$(QUALITY_PYTHON) -m unittest tests.common.test_template_styles
