# Organisation des tests

`make test` découvre automatiquement les tests sous `eures_beta` et `config`
et exécute toute la suite PostgreSQL, sans liste de modules à maintenir. `TEST_ARGS` permet de transmettre
les options du lanceur Django ; le rôle local doit pouvoir créer une base de test.

- `eures_beta/test_entrypoints.py` : accueil, langues et accès à l’administration.
- `eures_beta/test_layout.py` : organisation du projet et emplacement des ressources.
- `eures_beta/test_logging.py` : masquage des liens sensibles dans les journaux.
- `config/test_*.py` : santé, statiques, HTTPS et démonstration partagée.
- `eures_beta/journeys/tests/` : accès, offres, matching, conversations, langues et données fictives.
- `eures_beta/journeys/test_employer_*.py` : scénarios détaillés du nouveau parcours employeur.
- Les tests du lecteur de documents et du diagnostic Push gardent leurs modules dédiés.

Le dossier `journeys/tests/base.py` partage seulement la préparation du scénario
fictif. Chaque méthode de test est conservée dans un seul module ; il n’est pas
nécessaire de maintenir une liste d’imports dans `tests/__init__.py`.
Les trois fichiers à la racine du paquet ne représentent donc pas toute la suite.
