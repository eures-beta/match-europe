# Tests automatisés

Tous les tests Python et JavaScript sont réunis ici, par domaine. Ce dossier
est un paquet Python, pas une application Django.

- `candidates/`, `employers/`, `matching/`, `users/`, `invitations/`, `skills/`, `occupations/`,
  `documents/`, `emails/`, `integrations/`, `observability/` : tests métier et
  tests des services de chaque domaine, avec leurs fixtures spécifiques ;
- `common/` : navigation, pages publiques, présentation et traductions ;
- [config/](config/) : réglages, déploiement, découverte et interface Make,
  dont les diagnostics CI et la lecture des descriptions de PR ;
- `e2e/` : parcours HTTP dans Docker sous plafond mémoire et tests du banc ;
- `helpers.py` : assertions communes aux tests Python.

Lancer `make test` pour Python et `make test-js` pour JavaScript. Les tests
Docker ont leurs entrées distinctes : `make e2e-test` et `make e2e-regression`.
Les comptes fictifs utilisables dans l'application restent sous `eures_beta/`.

Les régressions PDF ajoutées dans `main` sont conservées dans
[documents/test_pdf_compatibility.py](documents/test_pdf_compatibility.py).
Les contrats des nouveaux outils sont dans
[config/test_ci_diagnostics.py](config/test_ci_diagnostics.py) et
[config/test_pr_description.py](config/test_pr_description.py).

Voir [le guide des commandes et sélections](../docs/TESTS.md).

`common/test_workspace_routes.py` vérifie les adresses canoniques des espaces,
les deux interfaces matching et les redirections de compatibilité sans perte de POST.

`candidates/service_worker.test.cjs` vérifie les destinations Push canoniques,
la compatibilité des anciennes notifications et le refus des destinations externes.
