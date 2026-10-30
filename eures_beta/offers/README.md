# Offres et questions

Cette application porte les offres et leurs questions de préqualification, avec leurs formulaires, services, vues et permissions. Ces objets alimentent le parcours de rapprochement. Ils sont distincts des brouillons `EmployerImport` du [parcours employeur](../employers/).

## Contenu de ce dossier

### Dossiers

- [migrations/](migrations/) — Ces fichiers décrivent l’évolution du schéma et de l’état Django pour les offres et questions.
- [tests/](tests/) — Ces tests vérifient les offres et questions.

### Fichiers

- [__init__.py](__init__.py) — Identifie ce dossier comme un paquet Python.
- [apps.py](apps.py) — Déclare l’application auprès de Django et son identité technique.
- [forms.py](forms.py) — Définit les formulaires et la validation des saisies de ce domaine.
- [models.py](models.py) — Décrit les modèles persistants et leurs relations pour ce domaine.
- [permissions.py](permissions.py) — Centralise les contrôles d’autorisation propres aux objets du domaine.
- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [services.py](services.py) — Regroupe les opérations métier réutilisables du domaine.
- [urls.py](urls.py) — Associe les chemins HTTP aux vues correspondantes.
- [views.py](views.py) — Traite les requêtes HTTP et prépare les réponses de ce domaine.

[Remonter au dossier parent](../).
