.PHONY: translations-compile
translations-compile: ## Compiler les catalogues gettext après modification des fichiers .po
	@$(MANAGE) compilemessages --ignore '.venv*'

translations-extract: ## Actualiser les catalogues FR/DE depuis le code et les templates
	@$(MANAGE) makemessages --locale fr --locale de --extension html,txt,py,subject --no-wrap --no-obsolete --ignore build --ignore staticfiles --ignore '.venv*'

translations-check: ## Refuser les messages gettext non traduits ou encore marqués fuzzy
	$(PYTHON) -m eures_beta.translation_check
