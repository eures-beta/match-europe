# Notifications dans le site

Cette application enregistre les notifications destinées aux utilisateurs et permet de les consulter ou de les marquer comme lues. Une notification en base n’est pas à elle seule une notification Push livrée par le navigateur. Le diagnostic Push est un sujet distinct, porté actuellement par le [code employeur](../employers/).

## Contenu de ce dossier

### Dossiers

- [migrations/](migrations/) — Ces fichiers décrivent l’évolution du schéma et de l’état Django pour les notifications.
- [tests/](tests/) — Ces tests vérifient les notifications.

### Fichiers

- [__init__.py](__init__.py) — Identifie ce dossier comme un paquet Python.
- [apps.py](apps.py) — Déclare l’application auprès de Django et son identité technique.
- [models.py](models.py) — Décrit les modèles persistants et leurs relations pour ce domaine.
- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [services.py](services.py) — Regroupe les opérations métier réutilisables du domaine.
- [urls.py](urls.py) — Associe les chemins HTTP aux vues correspondantes.
- [views.py](views.py) — Traite les requêtes HTTP et prépare les réponses de ce domaine.

[Remonter au dossier parent](../).
