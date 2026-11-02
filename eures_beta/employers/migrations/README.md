# Migrations — employers

Cette migration initiale définit directement le schéma employeur actuel.
Une installation neuve crée ses sept tables ; une base existante doit avoir
appliqué la transition autonome avant le retrait des archives. Depuis la racine,
`make migrations` affiche l'état et `make check` détecte les migrations manquantes.
Voir [le guide de transition](../../../docs/AUTONOMOUS_MIGRATIONS.md).

## Contenu de ce dossier

### Fichiers

- [0001_autonomous_schema.py](0001_autonomous_schema.py) — Définit les sept modèles employeur actuels et protège les bases sans marqueur de transition.
- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [__init__.py](__init__.py) — Identifie ce dossier comme un paquet Python.


[Remonter au dossier parent](../).
