# Parcours candidat

Cette application porte le modèle candidat, sa modification et le nouvel accueil candidat. L’accueil propose les entrées CV, LinkedIn et saisie manuelle : ces trois entrées sont encore une maquette, pas un import complet. Ses templates et statiques sont rangés dans cette application. Voir [le périmètre de l’accueil](../../docs/CANDIDATE_LANDING.md).

## Contenu de ce dossier

### Dossiers

- [migrations/](migrations/) — Ces fichiers décrivent l’évolution du schéma et de l’état Django pour les données et pages candidat.
- [static/](static/) — Ce dossier est découvert par Django pour les fichiers statiques de l’application candidats.
- [templates/](templates/) — Ce dossier rassemble les templates appartenant à l’application candidats.
- [tests/](tests/) — Ces tests vérifient les données et pages candidat.

### Fichiers

- [__init__.py](__init__.py) — Identifie ce dossier comme un paquet Python.
- [apps.py](apps.py) — Déclare l’application auprès de Django et son identité technique.
- [forms.py](forms.py) — Définit les formulaires et la validation des saisies de ce domaine.
- [landing.py](landing.py) — Prépare les données de présentation du nouvel accueil candidat.
- [models.py](models.py) — Décrit les modèles persistants et leurs relations pour ce domaine.
- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [urls.py](urls.py) — Associe les chemins HTTP aux vues correspondantes.
- [views.py](views.py) — Traite les requêtes HTTP et prépare les réponses de ce domaine.

[Remonter au dossier parent](../).
