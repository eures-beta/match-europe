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

`make help` décrit les cibles disponibles. `make serve` utilise Gunicorn.
Les versions Python sont verrouillées dans `requirements/`, Prettier dans npm.
`requirements/test.txt` inclut les dépendances applicatives ; les dépendances du
diagnostic Push supprimé ne sont plus installées. Aucun compte n'est créé au démarrage.

## Comptes et parcours réels

La connexion par lien magique est commune aux rôles ; un employeur doit disposer
d'un compte actif. Les invitations sont explicites. Les candidats suivent le
questionnaire public et la vérification de leur email avant création du profil.
Voir [connexion](MAGIC_LOGIN.md), [invitations](EMPLOYER_INVITATIONS.md) et
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
make test-retired-paths
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
