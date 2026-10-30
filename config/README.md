# Configuration du projet Django

Ce dossier contient la configuration unique du site : `settings.py` pour les réglages, `urls.py` pour les routes, `wsgi.py` et `asgi.py` pour les serveurs. `health.py` porte la sonde de santé ; les fichiers `test_*.py` vérifient notamment le démarrage et les modes de fonctionnement. Le code métier se trouve dans [eures_beta](../eures_beta/). Le seul `manage.py` est à la racine du dépôt.

## Contenu de ce dossier

### Fichiers

- [__init__.py](__init__.py) — Identifie ce dossier comme un paquet Python.
- [asgi.py](asgi.py) — Expose l’application Django aux serveurs compatibles ASGI.
- [demo.py](demo.py) — Regroupe les mécanismes du scénario fictif et ses réglages associés.
- [health.py](health.py) — Implémente la sonde de santé du service.
- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [settings.py](settings.py) — Définit les réglages Django à partir de la configuration de l’environnement.
- [test_demo_modes.py](test_demo_modes.py) — Tests portant sur réglages des modes fictifs et protections associées.
- [test_deployment.py](test_deployment.py) — Tests portant sur dépendances et démarrage du déploiement.
- [test_preview_workflows.py](test_preview_workflows.py) — Tests portant sur workflows des recettes jetables.
- [test_shared_demo.py](test_shared_demo.py) — Tests portant sur scénario fictif partagé.
- [test_test_collection.py](test_test_collection.py) — Tests portant sur découverte et import des tests.
- [urls.py](urls.py) — Associe les chemins HTTP aux vues correspondantes.
- [wsgi.py](wsgi.py) — Expose l’application Django aux serveurs compatibles WSGI.

[Remonter au dossier parent](../).
