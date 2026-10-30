# Documents et pièces jointes

Cette application gère les documents, leur téléversement et leur téléchargement. Les lecteurs PDF et les fonctions d’extraction de champs sont également ici ; les imports employeurs peuvent les réutiliser. Les fichiers utilisateur eux-mêmes ne sont pas stockés dans ce dossier de sources. Voir [le lecteur de documents](../../docs/EMPLOYER_DOCUMENT_READER.md).

## Contenu de ce dossier

### Dossiers

- [migrations/](migrations/) — Ces fichiers décrivent l’évolution du schéma et de l’état Django pour les documents et leur lecture.
- [tests/](tests/) — Ces tests vérifient les documents et leur lecture.

### Fichiers

- [__init__.py](__init__.py) — Identifie ce dossier comme un paquet Python.
- [apps.py](apps.py) — Déclare l’application auprès de Django et son identité technique.
- [document_fields.py](document_fields.py) — Extrait et organise les champs utiles issus des documents.
- [forms.py](forms.py) — Définit les formulaires et la validation des saisies de ce domaine.
- [models.py](models.py) — Décrit les modèles persistants et leurs relations pour ce domaine.
- [pdf_reader.py](pdf_reader.py) — Lit le contenu des PDF pour les parcours d’import.
- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [services.py](services.py) — Regroupe les opérations métier réutilisables du domaine.
- [urls.py](urls.py) — Associe les chemins HTTP aux vues correspondantes.
- [views.py](views.py) — Traite les requêtes HTTP et prépare les réponses de ce domaine.

[Remonter au dossier parent](../).
