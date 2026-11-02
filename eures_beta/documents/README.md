# Lecture des documents

Ce paquet fournit les lecteurs PDF et l’extraction de champs réutilisés par le parcours employeur. L’ancien modèle de pièce jointe et ses routes sont supprimés ; leur historique est supprimé ; les tests de lecture des documents restent actifs.

## Contenu de ce dossier

### Dossiers

- [tests/](tests/) — Ces tests vérifient les documents et leur lecture.

### Fichiers

- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [__init__.py](__init__.py) — Identifie ce dossier comme un paquet Python.
- [apps.py](apps.py) — Déclare l’application auprès de Django et son identité technique.
- [document_fields.py](document_fields.py) — Extrait et organise les champs utiles issus des documents.
- [pdf_reader.py](pdf_reader.py) — Lit le contenu des PDF pour les parcours d’import.

[Remonter au dossier parent](../).
