# Rapprochements et accords

Cette application gère les rapprochements entre offres et candidats, les réponses, leur revue et les accords précédant une conversation. `models.py` décrit les objets persistants, `services.py` les opérations métier, et les vues et formulaires leur utilisation à l’écran. Elle s’appuie sur les domaines candidats, offres et conversations plutôt que de les redéfinir.

## Contenu de ce dossier

### Dossiers

- [migrations/](migrations/) — Ces fichiers décrivent l’évolution du schéma et de l’état Django pour les rapprochements, réponses et accords.
- [tests/](tests/) — Ces tests vérifient les rapprochements, réponses et accords.

### Fichiers

- [__init__.py](__init__.py) — Identifie ce dossier comme un paquet Python.
- [apps.py](apps.py) — Déclare l’application auprès de Django et son identité technique.
- [forms.py](forms.py) — Définit les formulaires et la validation des saisies de ce domaine.
- [models.py](models.py) — Décrit les modèles persistants et leurs relations pour ce domaine.
- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [services.py](services.py) — Regroupe les opérations métier réutilisables du domaine.
- [urls.py](urls.py) — Associe les chemins HTTP aux vues correspondantes.
- [views.py](views.py) — Traite les requêtes HTTP et prépare les réponses de ce domaine.

[Remonter au dossier parent](../).
