# Organisation des tests

`make test` découvre les tests sous `eures_beta` et `config` et exécute la suite
PostgreSQL. Chaque worktree utilise sa propre base locale de test ; le rôle doit
pouvoir la créer. Les appels externes sont simulés.

- `employers/tests/` : imports, établissements, accès, données et recherche ;
- `candidates/tests/` : accueil candidat et interactions simulées ;
- `documents/tests/` : lecture et extraction des documents ;
- `occupations/tests/` : catalogue métiers partagé ;
- `eures_beta/test_*.py` : pages publiques, langues, navigation et cas transverses ;
- `config/test_*.py` : santé, statiques, HTTPS, configuration et collecte des tests.

`test_retired_prototype.py` vérifie l'absence des anciens parcours de `/access/`
et le maintien des pages actuelles. Le diagnostic Push applicatif dans
`employers/push_test.py` est distinct des tests automatisés.

`make migrations-test` exécute `employers/tests/test_autonomous_migrations.py` :
création directe des seules tables actuelles, conservation des données, sessions
et permissions après la transition, et refus du retrait des archives si la base
n'a pas appliqué la première étape. Ces tests utilisent le chargeur Django normal.
Les tests propres aux anciennes migrations ont été retirés avec ces fichiers.
