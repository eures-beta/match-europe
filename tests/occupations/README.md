# Tests des référentiels métiers

- [test_reference_queries.py](test_reference_queries.py) : grammaire ROME/ESCO,
  séparation ESCO/ROME, limite HTTP de 150 caractères et répétitions hostiles.
- [test_search_performance.py](test_search_performance.py) : normalisation des
  intitulés, recherche à froid et routes FR/EN/DE dans un sous-processus borné.
- [test_api.py](test_api.py) et [test_catalog.py](test_catalog.py) : réponses API,
  catalogue local et intégrité des références.
- [test_picker.cjs](test_picker.cjs) : interactions du sélecteur JavaScript.

Exécuter `make test TESTS=tests.occupations` et `make test-js`.
[Service](../../eures_beta/occupations/) ; [triage](../../docs/CODEQL_TRIAGE.md).
