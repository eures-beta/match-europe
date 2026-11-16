# Consulter les contrôles GitHub Actions

Ces diagnostics sont destinés à l'équipe technique. Ils lisent GitHub avec la
session GitHub CLI existante (`gh auth login`), sans charger `.env`, sans Django,
sans PostgreSQL et sans dépendance Python supplémentaire. Python 3 et `gh` sont requis.

## État et erreurs

```bash
make ci-status RUN=43891895398
make ci-errors RUN=43891895398
```

`RUN` est l'identifiant numérique du run, visible dans son URL GitHub. L'état affiche
la tentative, le commit, chaque job et son URL. Ce diagnostic réussit si la lecture
réussit, même si la CI est rouge : il ne remplace pas un contrôle de livraison.

Par défaut, `ci-errors` inspecte les jobs terminés en échec, annulés ou interrompus.
Le filtre couvre assertions, tracebacks, erreurs, arrêts, signaux et codes de sortie.
Un job encore actif n'est pas interprété comme réussi. Pour choisir un job, y compris
un job réussi ou actif, utiliser son identifiant affiché par `ci-status` :

```bash
make ci-errors RUN=43891895398 JOB=133385027264
make ci-errors RUN=43891895398 JOB=133385027264 PATTERN='Killed|exit code|Segmentation|signal'
make ci-errors RUN=43891895398 JOB=133385027264 PATTERN=. CONTEXT=0 LINES=500
```

Les occurrences proches sont regroupées, numérotées et entourées de trois lignes
de contexte. Sortie limitée aux 200 dernières lignes correspondantes par job et
2 000 caractères par ligne, pour garder visibles les causes de terminaison.
`CONTEXT` accepte 0–20 et `LINES` 1–2 000. `PATTERN` est une expression régulière
Python insensible à la casse, transmise comme donnée sans être exécutée par le shell.
Les paramètres d'origine ne sont pas réexportés automatiquement par Make : seuls
leurs équivalents `CI_*`, transmis littéralement, sont utilisés par le programme.
Les séquences de contrôle du terminal sont retirées avant stockage et affichage.
Aucune correspondance ne prouve l'absence d'erreur : essayer `PATTERN=.` ou ouvrir
l'URL du job. Les logs peuvent être indisponibles, notamment pendant un run actif,
après expiration ou faute de droits. Une erreur réseau/API/lecture produit un échec
explicite, jamais un faux rapport « aucune erreur » ; aucun retry automatique.

## Cache local et autres dépôts

Les logs terminés sont téléchargés une fois, puis réutilisés pour les autres filtres.
Chaque appel relit les métadonnées actuelles. Le cache distingue dépôt, run, tentative
et job : une nouvelle tentative ne réutilise pas les anciens logs. Les logs actifs
ne sont jamais mis en cache. Pour forcer une nouvelle lecture :

```bash
make ci-errors RUN=43891895398 REFRESH=1
make ci-status REPO=eures-beta/match-europe-deploy-clever RUN=123456
```

Le dépôt par défaut est `eures-beta/match-europe`. Les journaux restent dans
`.runtime/ci-logs/`, ignoré par Git, répertoires privés (700), fichiers privés (600).
Ils peuvent contenir des informations sensibles : ne pas les committer ni les publier.
Pas de purge automatique ; ils peuvent être supprimés manuellement lorsqu'inutiles.
Le téléchargement est borné à 90 secondes, les logs acceptés à 32 Mio par job.
Les erreurs brutes de `gh` ne sont pas réaffichées.

## Autorisations et vérification

Ces cibles ne font que lire GitHub et écrire le cache local. Elles ne relancent,
n'annulent et ne modifient aucun job, PR ou environnement. Une autorisation locale
ciblée sur `make ci-status` et `make ci-errors` peut être accordée si le client la
propose ; aucune règle globale n'est installée par ce code, et les restrictions
réseau/fichiers du client restent applicables. Les recettes sont dans le Makefile.

Les tests du diagnostic simulent GitHub et n'utilisent pas de tables. L'entrée
commune conserve son précontrôle PostgreSQL local :

```bash
make test TEST_ARGS='-k ci_diagnostics'
```

La suite vérifie cache, nouvelles tentatives, pannes réseau, logs vides, filtres,
contrôles terminal, identifiants et transmission des paramètres Make sans exécution.
