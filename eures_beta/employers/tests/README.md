# Tests — employers

Ces tests vérifient les imports, accès et parcours employeur. Les fichiers sont regroupés par thème ; les tests de migrations, lorsqu’ils sont présents, vérifient aussi les installations neuves et la conservation des données après la transition autonome. Depuis la racine, `make test` exécute la suite complète sur PostgreSQL. Voir [le guide des tests](../../../docs/TESTS.md) pour la préparation et les limites des suites ciblées.

## Contenu de ce dossier

### Fichiers

- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [__init__.py](__init__.py) — Identifie ce dossier comme un paquet Python.
- [test_autonomous_migrations.py](test_autonomous_migrations.py) — Vérifie la création neuve, la conservation des données et le refus de sauter la transition.
- [test_employer_connected.py](test_employer_connected.py) — Tests portant sur parcours employeur connecté.
- [test_employer_contact.py](test_employer_contact.py) — Tests portant sur contact employeur.
- [test_employer_import.py](test_employer_import.py) — Tests portant sur import d’offres employeur.
- [test_employer_login.py](test_employer_login.py) — Tests portant sur connexion employeur.
- [test_employer_ownership.py](test_employer_ownership.py) — Tests portant sur habilitations employeur.
- [test_employer_search.py](test_employer_search.py) — Tests portant sur recherche employeur.
- [test_employer_workspace.py](test_employer_workspace.py) — Tests portant sur espace de travail employeur.
- [test_eures_import.py](test_eures_import.py) — Tests portant sur import spécifique des offres EURES.
- [test_push_test.py](test_push_test.py) — Tests portant sur diagnostic Push.


[Remonter au dossier parent](../).
