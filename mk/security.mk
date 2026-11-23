.PHONY: security-scan
security-scan: ## Chercher les secrets dans l’historique Git local complet, valeurs masquées
	$(GITLEAKS) git . --redact=100 --log-opts=--all --no-banner

# Passer le chemin comme donnée, jamais dans une recette shell interpolée.
.PHONY: security-alerts security-plan security-apply
security-alerts: ## Consulter les alertes CodeQL et préparer leurs métadonnées de revue (lecture seule)
	python3 -m config.security_alerts list

security-plan: ## Vérifier et afficher les décisions JSON, sans modifier GitHub (FILE=…)
	python3 -m config.security_alerts plan

security-apply: ## Appliquer uniquement les décisions explicites vérifiées du fichier JSON (FILE=…)
	python3 -m config.security_alerts apply
