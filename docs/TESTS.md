# Exécuter et sélectionner les tests

## Django et PostgreSQL

Installer les dépendances avec `make install-test`. Chaque worktree possède son
`.env` ignoré par Git et une `PGDATABASE` locale distincte ; le rôle PostgreSQL
doit pouvoir créer la base de test. Ne pas partager cette base entre exécutions
concurrentes. Les appels aux services externes sont simulés.

Sans paramètre, la commande découvre tous les tests Python du dossier `tests/`
à la racine du dépôt :

```bash
make test
```

`TESTS` remplace cette sélection par un ou plusieurs labels Django : paquet,
module, classe ou méthode. Par exemple :

```bash
make test TESTS=tests.matching
make test TESTS=tests.users.test_account.AccountPageTests
make test \
  TESTS=tests.users.test_account.AccountPageTests.test_anonymous_users_cannot_read_account_information
make test \
  TESTS='tests.employers.test_albert tests.integrations.test_albert'
```

Pour sélectionner par fragment du nom complet des tests, utiliser l'option Django
`-k` dans `TEST_ARGS`. Plusieurs `-k` sont combinés par un OU :

```bash
make test TEST_ARGS='-k albert'
make test TEST_ARGS='-k employer -k occupation'
make test TESTS=tests.users TEST_ARGS='-k account --verbosity=2'
```

`TEST_ARGS` accepte aussi les autres options Django, par exemple `--keepdb`.
Sa valeur par défaut est `--verbosity=0` ; `--noinput` est toujours transmis.
Une valeur `TESTS` vide est refusée avant le lancement du runner. Un sous-ensemble
ne remplace pas la suite complète avant publication.

Les tests sont séparés du code applicatif, comme dans Les Emplois :

- `tests/<domaine>/` : employeurs, candidats, comptes, matching, compétences,
  métiers, documents, e-mails, intégrations et observabilité ;
- `tests/common/` : pages publiques, navigation, langues et présentation communes ;
- `tests/config/` : configuration, déploiement, découverte et commandes Make ;
- `tests/helpers.py` : helpers partagés uniquement par les tests ;
- `tests/e2e/` : banc HTTP Docker et tests unitaires de ce banc.

`tests/` est un paquet Python, pas une application Django : ne pas l'ajouter à
`INSTALLED_APPS`. Les fixtures et helpers spécifiques restent avec leur domaine.
Les comptes fictifs utilisables en local/recette restent du code applicatif dans
`eures_beta/users/` ; ce ne sont pas des tests automatisés.
Les migrations se vérifient avec le même runner, par exemple :

```bash
make test TEST_ARGS='-k migration -k model_renames'
```

## JavaScript

Installer les dépendances avec `make install-js`, puis lancer le runner Node :

```bash
make test-js
make test-js JS_TESTS=tests/occupations/test_picker.cjs
```

Sans sélection, le Makefile découvre tous les fichiers `*.test.cjs` et
`test_*.cjs` sous `tests/`. `JS_TESTS` accepte un ou plusieurs chemins séparés
par des espaces ; une sélection vide est refusée. Ces tests utilisent un DOM
simulé, sans navigateur ni service distant. `make check-js` vérifie séparément
la syntaxe et la stabilité Prettier ; il ne lance pas les tests.

## Dispositifs distincts

- `make e2e-test` lance les parcours HTTP et le contrôle mémoire dans Docker.
- `make e2e-regression` vérifie le témoin négatif historique du banc mémoire.
- `make users-upgrade-test` reconstruit un ancien schéma pour vérifier sa mise
  à niveau ; ce diagnostic est distinct de la découverte Django habituelle.
  Son exécutable est `tests/users/verify_upgrade.py`.

`make test` ne lance ni ces dispositifs, ni les tests Node, ni les linters.
Les contrôles de qualité gardent leurs commandes (`make check`,
`make format-check`, `make format-html-check`, `make format-js-check`,
`make format-css-check`, `make translations-check`). La CI exécute les contrôles
nécessaires via les mêmes commandes documentées.

Pour ajouter des tests à un domaine, ajouter ses fichiers au bon endroit et
utiliser ces paramètres ; ne pas créer une nouvelle cible Make pour chaque module.
Les règles d'architecture restent dans [AGENTS.md](../AGENTS.md).
