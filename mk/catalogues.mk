.PHONY: continuous-source-prepare
continuous-source-prepare: ## Télécharger explicitement les trois exports publics ESCO épinglés et les vérifier
	@$(MANAGE) prepare_skill_source --download

.PHONY: skills-source-check

skills-source-check: ## Vérifier hors ligne les archives officielles complètes avant la recette
	@$(MANAGE) check_skill_source

.PHONY: skills-pilot-build skills-pilot-audit
skills-pilot-audit: ## Comparer les 50 fiches aux archives ESCO épinglées, sans réseau ni base
	$(PYTHON) -m eures_beta.skills.tools.audit_skills_pilot --esco-dir "$(CATALOG_SOURCES)" --report .runtime/skills-pilot-audit.json

skills-pilot-build: ## Reconstruire le pilote depuis CATALOG_SOURCES en staging, sans réseau
	@$(MANAGE) sync_skills_pilot --esco-dir "$(CATALOG_SOURCES)" --output .runtime/skills-pilot-staging


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

.PHONY: rome-descriptions-build common-source-build common-source-audit
rome-descriptions-build: ## Extraire les descriptions officielles ROME 26M10 depuis une archive vérifiée
	$(PYTHON) -m eures_beta.occupations.tools.build_descriptions --archive "$(ROME_DEFINITIONS_ARCHIVE)" --output eures_beta/occupations/data

common-source-build: ## Construire le catalogue portable compétences ESCO et ROME depuis les archives vérifiées
	$(PYTHON) -m eures_beta.skills.tools.build_common_source --esco-dir "$(CATALOG_SOURCES)" --rome-archive "$(ROME_DEFINITIONS_ARCHIVE)" --output eures_beta/skills/data

common-source-audit: ## Contrôler hors ligne toutes les tranches et relations du catalogue portable
	$(PYTHON) -m eures_beta.skills.tools.audit_common_source
