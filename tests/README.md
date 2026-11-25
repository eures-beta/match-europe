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

`matching/test_review_email.py` vérifie la proposition d’offre par email après
validation conseiller, sans Push, et le retour sécurisé au dialogue candidat.

Les régressions PDF ajoutées dans `main` sont conservées dans
[documents/test_pdf_compatibility.py](documents/test_pdf_compatibility.py).
Les contrats des nouveaux outils sont dans
[config/test_ci_diagnostics.py](config/test_ci_diagnostics.py) et
[config/test_pr_description.py](config/test_pr_description.py).

Voir [le guide des commandes et sélections](../docs/TESTS.md).

`config/preview_relay.test.cjs` exécute le JavaScript réel du relais GitHub avec
réseau et horloge simulés : erreurs temporaires, quatre tentatives au maximum,
attentes progressives, respect de Retry-After et arrêt immédiat sur erreur permanente.

`matching/test_author_roles.py` vérifie les rôles des auteurs, l'immuabilité du
compte candidat, les écritures directes et les migrations avec données non vides.

`common/test_template_styles.py` vérifie le vrai linter CSS des templates avec
l'environnement qualité dans `make format-html-check` ; ce contrôle est obligatoire
en CI templates, sans dépendance djLint dans l'application. `common/test_stylesheet_loading.py`
vérifie la découverte des feuilles statiques et leur ordre dans les pages publiques.

`common/test_workspace_routes.py` vérifie les adresses canoniques des espaces,
les deux interfaces matching et les redirections de compatibilité sans perte de POST.

`candidates/service_worker.test.cjs` vérifie les destinations Push canoniques,
la compatibilité des anciennes notifications et le refus des destinations externes.

- [config/test_security_alerts.py](config/test_security_alerts.py) vérifie les plans
  de classement CodeQL, les refus, la reprise et les paramètres littéraux Make,
  avec l’API GitHub simulée et sans modifier d’alerte réelle.

Le traitement post-Albert est couvert par `matching/test_review_workflow.py`, `matching/test_review_concurrency.py` et `matching/test_review_workflow_migration.py` : droits, notes privées, décisions, concurrence PostgreSQL, refus sur trois offres et migration non vide.
