# Développement de Match Europe

Un seul projet Django, une configuration `config/` et un `manage.py` à la racine.
Les applications métier vivent sous `eures_beta/`. Le prototype historique
Flask/Grist reste dans son dépôt distinct.

## Installation et commandes

Le Python déclaré dans [`.python-version`](../.python-version), PostgreSQL et Node.js 24
sont nécessaires. Copier `.env.example` en
`.env` et renseigner les paramètres locaux ; ne jamais copier de secrets de production.
Utiliser une base et des environnements virtuels propres à chaque worktree.

```bash
make install-test
make install-quality
make install-js
make db-create
make db-check
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
`DEMO_ACCOUNTS_ENABLED=1`, `EMAIL_DELIVERY_ENABLED=0` ;
le peuplement reste une action séparée avec `make test-accounts-seed` ou
`make matching-seed`. Les simulations Albert se configurent explicitement avec
`ALBERT_SIMULATED=1` pour tous les usages.
Sans simulation, un service Albert configuré peut être appelé réellement.

`make help` décrit les cibles disponibles. `make serve PORT=9042` utilise Gunicorn. Le diagnostic
`make occupations-memory-serve` et le hook `make clever-run` restent distincts :
ils vérifient des dispositifs WSGI spécifiques, pas des parcours Django.
Les versions Python sont verrouillées dans `requirements/`, Prettier dans npm.
`requirements/test.txt` inclut les dépendances applicatives ; les dépendances du
diagnostic Push supprimé ne sont plus installées. Aucun compte n'est créé au démarrage.

## Préparation PostgreSQL locale

Identifier une fois l’instance et le rôle de développement de la machine, puis
réutiliser ces valeurs dans les worktrees. Ne pas changer automatiquement de
serveur ou d’utilisateur quand une connexion échoue. Les anciennes commandes
`matching-db-*` pilotent une instance particulière sur 55441 ; ce port n’est pas
une exigence générale et cette instance ne doit pas être démarrée ou arrêtée
pour remplacer une autre instance utilisée par des sessions parallèles.

Renseigner explicitement dans chaque `.env` :

| Variable | Choix |
| --- | --- |
| `PGHOST` | Instance locale choisie : loopback ou répertoire de socket Unix |
| `PGPORT` | Port exact de cette instance |
| `PGUSER` | Rôle existant avec droit `CREATEDB`, nécessaire aux bases de test Django |
| `PGDATABASE` | Nom unique par worktree, distinct des bases système, au plus 58 octets |
| `PGPASSWORD` / `PGPASSFILE` | Authentification locale si nécessaire, jamais versionnée |
| `PGSSLMODE` | Transport TLS si nécessaire, conservé par les commandes |

Le nom `skeleton` n’est pas un compte fourni par le projet. L’exemple laisse
`PGUSER` et `PGDATABASE` vides pour demander un choix réel plutôt qu’une valeur
inexistante sur la machine. Un opérateur PostgreSQL prépare le rôle une fois ;
ces outils ne créent pas de rôle, ne donnent aucun droit et ne cherchent pas
un superutilisateur. Le rôle n’a pas besoin d’être superutilisateur.

- `make db-check` : lecture seule des droits, de l’existence, de la propriété et
  de l’accès à la base configurée ; ouverture effective de cette base et `SELECT 1`.
  Le contrôle se connecte d’abord à la base de maintenance `postgres` avec le
  même rôle. Si la base manque, il indique `make db-create` et échoue.
- `make db-create` : mêmes vérifications, puis création de la seule base configurée
  si elle manque. Si elle existe déjà et appartient au rôle, la commande réussit
  sans la recréer. Une base d’un autre rôle est refusée, jamais reprise ou effacée.
- `make test` : exécute `db-check` avant la suite Django. Un précontrôle en échec
  bloque les tests ; aucune réparation ou sélection d’un autre compte n’est cachée.

Les connexions du précontrôle ont un délai d’ouverture de cinq secondes. Les
messages ne contiennent ni mot de passe, ni chaîne de connexion, ni erreur brute
du serveur. Ces commandes acceptent uniquement une instance locale en environnement
`local` ou `preview`, jamais la production. Les tests HTTP Docker et le diagnostic
de migration historique conservent leurs dispositifs isolés.

Les approbations restent propres aux opérations : `db-check` lit, `db-create`
peut créer une base, `test` crée sa base temporaire. Les recettes sont visibles
dans le Makefile ; ne pas remplacer ces contrôles par une autorisation générale
sur des commandes SQL libres.

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

Pour consulter GitHub Actions, utiliser `make ci-status RUN=…` puis
`make ci-errors RUN=…`. Les erreurs de tests et causes d'arrêt sont recherchées
dans un cache local privé, sans rechargement à chaque filtre et sans mutation
GitHub. Voir [le diagnostic CI et ses paramètres](CI_DIAGNOSTICS.md).

```bash
make check
make test
make test TESTS=tests.config.test_retired_paths
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
Docker ; voir [le banc système](E2E_TESTS.md).
Les migrations se vérifient depuis une base neuve et lors des transitions prises
en charge. Ne pas réécrire les migrations appliquées.

Voir les guides [Python/HTML](HTML_FORMATTING.md), [JavaScript/CSS](JAVASCRIPT_FORMATTING.md),
la [séparation HTML/CSS et ses exceptions contrôlées](HTML_CSS.md),
la [parité des environnements](ENVIRONMENT_PARITY.md), [l'état des travaux](../HANDOFF.md)
et les [consignes de contribution](../AGENTS.md). L'historique des choix reste
consultable dans Git et le [registre des décisions](DECISIONS.md).

## Configuration simplifiée

Les parcours métier sont permanents : leurs anciens interrupteurs sont retirés.
`EMAIL_DELIVERY_ENABLED` est l’unique autorisation d’envoi, avec SMTP et origine
HTTPS configurés. `ALBERT_SIMULATED=1` simule tous les usages Albert ; son défaut
est `0`, sans simulation automatique en cas de panne. `TEAM_CONTACT_EMAIL` centralise
le contact d’équipe (retours candidat/employeur et demandes de confidentialité).
Les demandes d’invitation employeur utilisent aussi cette unique adresse.

Lors d’une mise à jour de configuration, remplacer les trois anciens paramètres
de simulation par cette valeur unique et renommer le contact. Les anciens noms
ne sont plus lus. Le choix de simulation doit être explicite si les anciennes
valeurs différaient. Retirer les interrupteurs métier et l’ancien interrupteur
d’e-mails de connexion des configurations privées. Aucune configuration distante
n’est modifiée par cette PR. Les comptes fictifs restent explicitement activés
avec `TEST_ACCOUNTS_ENABLED`, incompatibles avec les envois réels.

La politique de connexions PostgreSQL est identique en local, en recette et en
production : réutilisation pendant 60 secondes (`CONN_MAX_AGE`), contrôle de
validité (`CONN_HEALTH_CHECKS`) et délai d’ouverture de connexion de 10 secondes
(`connect_timeout`). Ce dernier ne limite pas la durée des requêtes SQL.
`PGSSLMODE` continue de configurer le transport TLS propre à la connexion.

Chaque thread peut conserver sa connexion : dimensionner le budget PostgreSQL
avec le nombre de workers, threads et instances, y compris les recettes et les
commandes d’opérateur. `make serve PORT=…` utilise Gunicorn pour une recette
locale fidèle ; `make run` reste le serveur de développement Django, dont les
threads par requête ne bénéficient pas de la même réutilisation. Le code des
settings ne distingue pas ces environnements. Aucune configuration serveur
PostgreSQL ni donnée n’est modifiée.
