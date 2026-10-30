# Tests — occupations

Ces tests vérifient le catalogue de métiers et son API. Les fichiers sont regroupés par thème ; les tests de migrations, lorsqu’ils sont présents, vérifient aussi la conservation des données lors du découpage historique. Depuis la racine, `make test` exécute la suite complète sur PostgreSQL. Voir [le guide des tests](../../../docs/TESTS.md) pour la préparation et les limites des suites ciblées.

## Contenu de ce dossier

### Fichiers

- [__init__.py](__init__.py) — Identifie ce dossier comme un paquet Python.
- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [test_api.py](test_api.py) — Tests portant sur API du catalogue de métiers.
- [test_catalog.py](test_catalog.py) — Tests portant sur catalogue ESCO/ROME.

[Remonter au dossier parent](../).
