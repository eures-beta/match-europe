# Conversations

Cette application regroupe les conversations et leurs messages, avec les formulaires, vues et permissions associés. Elle intervient après les accords du parcours de rapprochement. Le template de discussion reste dans les [templates partagés](../templates/conversations/). Voir [les choix d’extraction et de migration](../../docs/CONVERSATIONS_APP.md).

## Contenu de ce dossier

### Dossiers

- [migrations/](migrations/) — Ces fichiers décrivent l’évolution du schéma et de l’état Django pour les conversations et messages.
- [tests/](tests/) — Ces tests vérifient les conversations et messages.

### Fichiers

- [__init__.py](__init__.py) — Identifie ce dossier comme un paquet Python.
- [apps.py](apps.py) — Déclare l’application auprès de Django et son identité technique.
- [forms.py](forms.py) — Définit les formulaires et la validation des saisies de ce domaine.
- [models.py](models.py) — Décrit les modèles persistants et leurs relations pour ce domaine.
- [permissions.py](permissions.py) — Centralise les contrôles d’autorisation propres aux objets du domaine.
- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [urls.py](urls.py) — Associe les chemins HTTP aux vues correspondantes.
- [views.py](views.py) — Traite les requêtes HTTP et prépare les réponses de ce domaine.

[Remonter au dossier parent](../).
