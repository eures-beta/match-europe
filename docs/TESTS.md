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

Les tests des anciens parcours de `/access/` ont été retirés avec leur fixture
partagée. `test_retired_prototype.py` vérifie leur absence et le maintien des
pages actuelles ; `accounts/tests/test_retired_data.py` couvre le nettoyage ciblé
des comptes fictifs et la conservation des imports. `employers/push_test.py`
reste du code applicatif pour le diagnostic local, distinct des tests automatisés.

Les tests de migration vérifient sur PostgreSQL les valeurs, relations, tables
et permissions dans les deux sens, y compris après déplacement de l’historique
dans `migration_history`. Les appels externes sont simulés.
