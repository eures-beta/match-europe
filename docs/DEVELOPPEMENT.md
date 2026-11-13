# Développement de Match Europe

Un seul projet Django, une configuration `config/` et un `manage.py` à la racine.
Les applications métier vivent sous `eures_beta/`. Le prototype historique
Flask/Grist reste dans son dépôt distinct.

## Installation et commandes

Python 3.14, PostgreSQL et Node.js 24 sont nécessaires. Copier `.env.example` en
`.env` et renseigner les paramètres locaux ; ne jamais copier de secrets de production.
Utiliser une base et des environnements virtuels propres à chaque worktree.

```bash
make install-test
make install-quality
make install-js
make db-create
make migrate
make run
```

### Plusieurs sessions en parallèle

Une seule commande démarre toute l’application Django, quel que soit le parcours :

```bash
make run PORT=9041
```

`PORT` vaut 8000 par défaut ; `HOST` vaut `127.0.0.1`. Chaque session choisit
un port libre et conserve son worktree, son `.venv`, son `.env` et sa base dédiés.
Le port ne choisit ni rôle, ni données, ni simulation. Les anciennes commandes
`candidate-run`, `matching-run`, `continuous-run`, `albert-run` et les variantes
candidat, employeur et dialogue sont retirées.

Le serveur charge le `.env` du worktree sans imposer de réglages métier. Pour un
essai fictif, configurer explicitement `DJANGO_ENVIRONMENT=local`,
`TEST_ACCOUNTS_ENABLED=1`, `EMAIL_DELIVERY_ENABLED=0` et `LOGIN_EMAIL_ENABLED=0` ;
le peuplement reste une action séparée avec `make test-accounts-seed` ou
`make matching-seed`. Les simulations Albert se configurent explicitement avec
`SKILLS_ALBERT_SIMULATED=1` ou `CONFIRMATION_DIALOGUE_SIMULATED=1` selon l’essai.
Sans simulation, un service Albert configuré peut être appelé réellement.

`make help` décrit les cibles disponibles. `make serve PORT=9042` utilise Gunicorn. Le diagnostic
`make occupations-memory-serve` et le hook `make clever-run` restent distincts :
ils vérifient des dispositifs WSGI spécifiques, pas des parcours Django.
Les versions Python sont verrouillées dans `requirements/`, Prettier dans npm.
`requirements/test.txt` inclut les dépendances applicatives ; les dépendances du
diagnostic Push supprimé ne sont plus installées. Aucun compte n'est créé au démarrage.

## Comptes et parcours réels

La connexion par lien magique est commune aux rôles ; un employeur doit disposer
d'un compte actif. Les invitations sont explicites. Les candidats suivent le
questionnaire public et la vérification de leur email avant création du profil.
Voir [connexion](MAGIC_LOGIN.md), [invitations](INVITATIONS.md) et
[inscription candidat](CANDIDATE_EMAIL_REGISTRATION.md).

Les droits et l'affichage sont communs aux environnements. Les anciens formulaires
de connexion employeur, la boîte simulée, le diagnostic Push et le simulateur de
recherche sont retirés. Aucun réglage historique ne les réactive.
Les tables historiques restent conservées ; aucune purge n'est effectuée.
Les [comptes fictifs](TEST_ACCOUNTS.md) restent un outil d'essai explicitement
activé, isolé de la production et incompatible avec les envois réels.

La lecture et la sauvegarde d'une offre ne déclenchent pas AGLAE ou le géocodage.
Ces intégrations conservent leurs actions explicites et leur configuration propre.
Les services Albert et les emails nécessitent les accès et activations documentés ;
les tests simulent les frontières externes et n'utilisent aucun secret réel.

## Vérifications

```bash
make check
make test
make test TESTS=config.test_retired_paths
make format-check
make format-html-check
make format-js-check
make format-css-check
make check-js
make translations-check
```

`make test` utilise PostgreSQL et une base de test distincte. Le contrôle des
anciens parcours vérifie leur absence, la connexion commune et les protections
CSRF. `make e2e-test` exécute les parcours HTTP réels et le contrôle mémoire dans
Docker ; voir [le banc système](SYSTEM_TESTS.md).
Les migrations se vérifient depuis une base neuve et lors des transitions prises
en charge. Ne pas réécrire les migrations appliquées.

Voir les guides [Python/HTML](HTML_FORMATTING.md), [JavaScript/CSS](JAVASCRIPT_FORMATTING.md),
la [parité des environnements](ENVIRONMENT_PARITY.md), [l'état des travaux](../HANDOFF.md)
et les [consignes de contribution](../AGENTS.md). L'historique des choix reste
consultable dans Git et le [registre des décisions](DECISIONS.md).
