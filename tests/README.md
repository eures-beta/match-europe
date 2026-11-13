# Tests automatisés

Tous les tests Python et JavaScript sont réunis ici, par domaine. Ce dossier
est un paquet Python, pas une application Django.

- `candidates/`, `employers/`, `matching/`, `users/`, `invitations/`, `skills/`, `occupations/`,
  `documents/`, `emails/`, `integrations/`, `observability/` : tests métier et
  tests des services de chaque domaine, avec leurs fixtures spécifiques ;
- `common/` : navigation, pages publiques, présentation et traductions ;
- `config/` : réglages, déploiement, découverte et interface Make ;
- `e2e/` : parcours HTTP dans Docker sous plafond mémoire et tests du banc ;
- `helpers.py` : assertions communes aux tests Python.

Lancer `make test` pour Python et `make test-js` pour JavaScript. Les tests
Docker ont leurs entrées distinctes : `make e2e-test` et `make e2e-regression`.
Les comptes fictifs utilisables dans l'application restent sous `eures_beta/`.

Voir [le guide des commandes et sélections](../docs/TESTS.md).

`common/test_workspace_routes.py` vérifie les adresses canoniques des espaces,
les deux interfaces matching et les redirections de compatibilité sans perte de POST.
