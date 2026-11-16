# Maintenance de Python

`.python-version` est la déclaration commune du runtime : Clever Cloud la lit,
les workflows utilisent `python-version-file`, le Makefile en déduit l'interpréteur
local et le banc Docker reçoit cette même version. `.python-image-digest` verrouille
l'image officielle utilisée par ce banc ; ce fichier ne contient pas de version
Python supplémentaire. Les deux fichiers sont mis à jour dans un seul commit.

La valeur initiale reste `3.14` : cette PR ne change pas la version déployée.
Le premier passage proposera une version exacte : les correctifs suivants seront
eux aussi proposés en PR. Python 4 nécessitera une décision explicite. Une nouvelle
empreinte de l'image système est aussi proposée à version Python inchangée.

Chaque lundi à 07:15 UTC, `Mise à jour hebdomadaire de Python` consulte les tags
stables officiels de CPython. Les alphas, bêtas et release candidates sont exclus.
Une image Linux amd64 et arm64 doit exister avant toute proposition. Une erreur
réseau ou une image indisponible fait échouer le contrôle, sans modifier le dépôt.

Le robot ouvre une PR sur `main`, comme Dependabot. Cette base stable évite de
choisir automatiquement parmi des piles en cours de réorganisation. Une branche
par version et empreinte évite les doublons ; une branche existante n'est jamais écrasée.
Les tests PostgreSQL, les parcours HTTP sous 256 Mio et les contrôles de qualité
sont déclenchés explicitement sur la branche proposée. Aucun merge automatique.
Le job hebdomadaire n'accède ni aux secrets applicatifs ni à la base de production.

Avant fusion, vérifier les tests, la compatibilité des dépendances et la présence
du runtime chez Clever Cloud. Les environnements locaux existants ne sont pas
recréés silencieusement : relancer `make install` avec le nouvel interpréteur
installé. `PYTHON_BOOTSTRAP` permet de préciser son chemin.

## Commandes

```bash
make test TESTS=tests.config.test_python_runtime
```

Ce test est sans réseau et couvre la sélection stable, les correctifs, les refus
de rétrogradation et les métadonnées invalides.

```bash
make python-update-check
```

Consulte les services officiels sans écrire les fichiers (GitHub CLI connecté).

```bash
make python-update
```

Prépare les deux fichiers localement, sans commit, push, PR ni déploiement.

## Activation

Le calendrier devient actif après fusion de cette PR et de ses parents dans main.
Le dépôt doit autoriser GitHub Actions à créer des pull requests : Settings →
Actions → General → Workflow permissions → Allow GitHub Actions to create and
approve pull requests. Le workflow ne demande et ne donne aucune approbation.
Aucun PAT, compte supplémentaire ou service Renovate n'est nécessaire.
Le lancement manuel se fait dans Actions → Mise à jour hebdomadaire de Python →
Run workflow, sur main. Les résultats de validation restent dans Actions même
si GitHub ne les rattache pas tous automatiquement à la PR créée par son jeton.

Le contrôleur Dependabot reste chargé des paquets (dont Django), des Actions et
des images Docker dont le nom est littéral. Ce nouvel outil gère le runtime
paramétré du banc E2E, pas les dépendances applicatives.
