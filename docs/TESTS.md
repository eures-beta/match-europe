# Organisation des tests

`make test` découvre les tests sous `eures_beta` et `config` et exécute la suite
PostgreSQL. `TEST_ARGS` transmet les options du lanceur Django ; le rôle local
doit pouvoir créer une base de test.

- Chaque application métier a son dossier `tests/` : comptes, employeurs,
  candidats, offres, matching, conversations, documents et notifications.
- `employers/tests/test_employer_*.py` : parcours employeur, établissements et accès.
- `documents/tests/test_document_reader.py` : extraction des documents.
- `employers/tests/test_push_test.py` : diagnostic Push, restreint au mode local.
- `eures_beta/test_*.py` : entrées, organisation, journalisation, scénarios
  transverses et traduction des pages.
- `config/test_*.py` : santé, statiques, HTTPS et configuration partagée.

`eures_beta/testing_support.py` partage la préparation des scénarios fictifs.
Chaque méthode reste dans un seul module, sans liste d’imports à maintenir
dans `tests/__init__.py`. `employers/push_test.py` est du code applicatif.

Les tests de migration vérifient sur PostgreSQL les valeurs, relations, tables
et permissions dans les deux sens, y compris après déplacement de l’historique
dans `migration_history`. Les appels externes sont simulés.
