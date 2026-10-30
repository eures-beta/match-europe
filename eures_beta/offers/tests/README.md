# Tests — offers

Ces tests vérifient les offres et questions. Les fichiers sont regroupés par thème ; les tests de migrations, lorsqu’ils sont présents, vérifient aussi la conservation des données lors du découpage historique. Depuis la racine, `make test` exécute la suite complète sur PostgreSQL. Voir [le guide des tests](../../../docs/TESTS.md) pour la préparation et les limites des suites ciblées.

## Contenu de ce dossier

### Fichiers

- [__init__.py](__init__.py) — Identifie ce dossier comme un paquet Python.
- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [test_migrations.py](test_migrations.py) — Tests portant sur conservation des données pendant les migrations.
- [test_offers.py](test_offers.py) — Tests portant sur offres et questions.

[Remonter au dossier parent](../).
