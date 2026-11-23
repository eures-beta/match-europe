.PHONY: invitation-email
.PHONY: login-email
login-email: ## Simuler un email privé de connexion, sans envoi (EMAIL et ORIGIN requis)
	@test -n "$(EMAIL)" && test -n "$(ORIGIN)" || { echo 'Indiquer EMAIL et ORIGIN.' >&2; exit 2; }
	@$(MANAGE) login_email "$(EMAIL)" --origin "$(ORIGIN)" --language "$(LANGUAGE)"

invitation-email: ## Simuler un email privé contenant un lien secret (INVITATION=UUID et ORIGIN requis)
	@test -n "$(INVITATION)" && test -n "$(ORIGIN)" || { echo 'Indiquer INVITATION=UUID et ORIGIN=https://hote-autorise.' >&2; exit 2; }
	@$(MANAGE) invitation_email "$(INVITATION)" --origin "$(ORIGIN)"

.PHONY: candidate-email candidate-registration-cleanup

candidate-email: ## Simuler un email de confirmation candidat (EMAIL et ORIGIN requis, lien privé)
	@test -n "$(EMAIL)" && test -n "$(ORIGIN)" || { echo 'Indiquer EMAIL et ORIGIN.' >&2; exit 2; }
	@$(MANAGE) candidate_email "$(EMAIL)" --origin "$(ORIGIN)"

candidate-registration-cleanup: ## Compter les demandes candidat expirées (CLEANUP_ARGS=--apply pour effacer)
	@$(MANAGE) cleanup_candidate_registrations $(CLEANUP_ARGS)
