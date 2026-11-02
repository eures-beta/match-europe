# Migrations — employers

Ces fichiers décrivent l’évolution du schéma et de l’état Django pour les imports, accès et parcours employeur. Ils sont versionnés pour reproduire la même évolution sur chaque base. Les migrations initiales participent au transfert depuis l’historique `journeys` ; elles ne signifient pas nécessairement une nouvelle table physique. Depuis la racine, `make migrations` affiche leur état et `make check` détecte les changements de modèles sans migration. Voir [la compatibilité des données](../../../docs/DOMAIN_EXTRACTION.md).

## Contenu de ce dossier

### Fichiers

- [0001_autonomous_schema.py](0001_autonomous_schema.py) — Définit les sept modèles employeur actuels et remplace les 36 migrations historiques.
- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [__init__.py](__init__.py) — Identifie ce dossier comme un paquet Python.

- [0001_autonomous_schema.py](0001_autonomous_schema.py) — Crée le schéma employeur actuel sur une base neuve et protège les bases sans marqueur de transition.

[Remonter au dossier parent](../).
