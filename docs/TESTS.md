# Exécuter et sélectionner les tests

## Django et PostgreSQL

Installer les dépendances avec `make install-test`. Chaque worktree possède son
`.env` ignoré par Git et une `PGDATABASE` locale distincte ; le rôle PostgreSQL
doit pouvoir créer la base de test. Ne pas partager cette base entre exécutions
concurrentes. Les appels aux services externes sont simulés.

Sans paramètre, la commande découvre tous les tests de `eures_beta` et `config` :

```bash
make test
```

`TESTS` remplace cette sélection par un ou plusieurs labels Django : paquet,
module, classe ou méthode. Par exemple :

```bash
make test TESTS=eures_beta.matching
make test TESTS=eures_beta.users.tests.test_account.AccountPageTests
make test \
  TESTS=eures_beta.users.tests.test_account.AccountPageTests.test_anonymous_users_cannot_read_account_information
make test \
  TESTS='eures_beta.employers.tests.test_albert eures_beta.integrations.tests.test_albert'
```

Pour sélectionner par fragment du nom complet des tests, utiliser l'option Django
`-k` dans `TEST_ARGS`. Plusieurs `-k` sont combinés par un OU :

```bash
make test TEST_ARGS='-k albert'
make test TEST_ARGS='-k employer -k occupation'
make test TESTS=eures_beta.users TEST_ARGS='-k account --verbosity=2'
```

`TEST_ARGS` accepte aussi les autres options Django, par exemple `--keepdb`.
Sa valeur par défaut est `--verbosity=0` ; `--noinput` est toujours transmis.
Une valeur `TESTS` vide est refusée avant le lancement du runner. Un sous-ensemble
ne remplace pas la suite complète avant publication.

Les tests métier vivent dans le dossier `tests/` de leur application :
`employers`, `candidates`, `users`, `matching`, `skills`, `occupations`, `documents`
et les autres domaines. Les tests des pages publiques et langues sont sous
`eures_beta/test_*.py` ; ceux du socle et des commandes sous `config/test_*.py`.
Les migrations se vérifient avec le même runner, par exemple :

```bash
make test TEST_ARGS='-k migration -k model_renames'
```

## JavaScript

Installer les dépendances avec `make install-js`, puis lancer le runner Node :

```bash
make test-js
make test-js JS_TESTS=eures_beta/occupations/test_picker.cjs
```

Sans sélection, le Makefile découvre tous les fichiers `*.test.cjs` et
`test_*.cjs` sous `eures_beta`. `JS_TESTS` accepte un ou plusieurs chemins séparés
par des espaces ; une sélection vide est refusée. Ces tests utilisent un DOM
simulé, sans navigateur ni service distant. `make check-js` vérifie séparément
la syntaxe et la stabilité Prettier ; il ne lance pas les tests.

## Dispositifs distincts

- `make e2e-test` lance les parcours HTTP et le contrôle mémoire dans Docker.
- `make e2e-regression` vérifie le témoin négatif historique du banc mémoire.
- `make users-upgrade-test` reconstruit un ancien schéma pour vérifier sa mise
  à niveau ; ce diagnostic est distinct de la découverte Django habituelle.

`make test` ne lance ni ces dispositifs, ni les tests Node, ni les linters.
Les contrôles de qualité gardent leurs commandes (`make check`,
`make format-check`, `make format-html-check`, `make format-js-check`,
`make format-css-check`, `make translations-check`). La CI exécute les contrôles
nécessaires via les mêmes commandes documentées.

Pour ajouter des tests à un domaine, ajouter ses fichiers au bon endroit et
utiliser ces paramètres ; ne pas créer une nouvelle cible Make pour chaque module.
Les règles d'architecture restent dans [AGENTS.md](../AGENTS.md).
