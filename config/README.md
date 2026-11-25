# Configuration et outillage transverse

`settings.py`, `urls.py`, `asgi.py` et `wsgi.py` configurent le projet Django.
`documentation.py` vérifie les budgets des consignes et guides.
`python_runtime.py` vérifie l'interpréteur et prépare les mises à jour hebdomadaires
de Python et de son image Docker, filtrées par les branches maintenues du catalogue
officiel Clever Cloud ; il fonctionne sans Django ni base de données.
Voir [la maintenance Python](../docs/PYTHON_RUNTIME.md) et `make help`.

`security_alerts.py` consulte, vérifie et applique les décisions individuelles
sur les alertes CodeQL via `gh`, sans Django ni triage automatique ; voir
[les commandes et protections](../docs/SECURITY_ALERTS.md).
