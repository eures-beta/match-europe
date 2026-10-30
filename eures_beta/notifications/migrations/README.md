# Migrations — notifications

Ces fichiers décrivent l’évolution du schéma et de l’état Django pour les notifications. Ils sont versionnés pour reproduire la même évolution sur chaque base. Les migrations initiales participent au transfert depuis l’historique `journeys` ; elles ne signifient pas nécessairement une nouvelle table physique. Depuis la racine, `make migrations` affiche leur état et `make check` détecte les changements de modèles sans migration. Voir [la compatibilité des données](../../../docs/DOMAIN_EXTRACTION.md).

## Contenu de ce dossier

### Fichiers

- [0001_initial.py](0001_initial.py) — Établit l’état initial de migration de cette application.
- [__init__.py](__init__.py) — Identifie ce dossier comme un paquet Python.
- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.

[Remonter au dossier parent](../).
