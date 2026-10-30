# Comptes et accès

Cette application gère les profils liés aux utilisateurs Django, leurs rôles, les jetons d’accès et les événements d’audit. `access_control.py`, les vues, formulaires et services portent les contrôles et parcours associés. L’authentification Django et le profil métier restent deux notions distinctes. La commande d’initialisation fictive est dans `management/commands/`.

## Contenu de ce dossier

### Dossiers

- [management/](management/) — Django découvre les commandes de cette application dans `commands/`.
- [migrations/](migrations/) — Ces fichiers décrivent l’évolution du schéma et de l’état Django pour les profils, accès et événements.
- [tests/](tests/) — Ces tests vérifient les profils, accès et événements.

### Fichiers

- [__init__.py](__init__.py) — Identifie ce dossier comme un paquet Python.
- [access_control.py](access_control.py) — Centralise les contrôles des accès utilisateurs.
- [apps.py](apps.py) — Déclare l’application auprès de Django et son identité technique.
- [forms.py](forms.py) — Définit les formulaires et la validation des saisies de ce domaine.
- [models.py](models.py) — Décrit les modèles persistants et leurs relations pour ce domaine.
- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [services.py](services.py) — Regroupe les opérations métier réutilisables du domaine.
- [urls.py](urls.py) — Associe les chemins HTTP aux vues correspondantes.
- [views.py](views.py) — Traite les requêtes HTTP et prépare les réponses de ce domaine.

[Remonter au dossier parent](../).
