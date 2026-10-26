# Consignes de développement

## Pull requests et collaboration en équipe

### Création

- Créer une branche dédiée au travail demandé, avec le préfixe `codex/` sauf
  instruction contraire. La destination habituelle est `main`.
- L'agent peut choisir un titre court et descriptif sans demander de confirmation.
  Respecter un titre fourni par l'humain ; celui-ci peut aussi le modifier ensuite.
- L'agent peut rédiger automatiquement la description : problème, changement
  apporté, vérifications et limites utiles à la relecture.
- Assigner la PR au compte GitHub de l'humain qui demande le travail. Vérifier
  son identifiant ; s'il est inconnu ou ambigu, le demander sans l'inventer.
  L'agent agit comme assistant de cet humain.
- Demander la relecture au compte GitHub `dejafait` par défaut, sauf consigne
  explicite différente. Si GitHub empêche cette demande ou l'assignation,
  signaler la limite sans prétendre que l'opération a réussi.
- Les PR empilées sont permises : une branche B peut cibler la branche A d'une
  PR encore ouverte, plutôt que `main`. Vérifier le contexte et demander la
  branche de base lorsque ce choix est ambigu ; ne pas poser systématiquement
  la question si la destination est déjà claire.

### Pendant la relecture

- Ne pas rebaser automatiquement les PR sur les nouveaux commits de leur
  branche de destination pendant leur vie courante. Le faire sur demande ou
  dans la préparation de la fusion décrite ci-dessous.
- Communiquer à l'humain les commentaires des reviewers, en expliquer les
  conséquences et proposer les suites à donner. Distinguer les corrections
  nécessaires des suggestions et des points de désaccord.

### Fusion et nettoyage

- Une demande de création ou de relecture de PR n'autorise pas sa fusion.
- Lorsqu'une fusion est autorisée, actualiser la branche de destination et
  rebaser la branche de travail sur ses derniers commits avant la fusion.
  Résoudre les conflits, revoir le diff et refaire les vérifications pertinentes.
- Ne jamais créer de merge commit. Ne pas squasher les commits sauf demande
  explicite de l'humain. Utiliser une fusion conservant un historique linéaire
  sans squash ; si les réglages GitHub l'empêchent, signaler le blocage sans
  contourner les règles du dépôt.
- Si le rebase impose de réécrire une branche déjà publiée, utiliser uniquement
  `--force-with-lease`, après vérification de l'état distant.
- Après la fusion d'une PR A, retargeter les PR empilées qui ciblaient sa branche
  vers sa destination effective (généralement `main`). Vérifier leur diff pour
  éviter de représenter les changements déjà intégrés. Si nécessaire, adapter
  uniquement les branches dépendantes concernées pour préserver leur travail.
- Supprimer la branche distante fusionnée lorsqu'elle ne sert plus de base à
  une PR ouverte. Ne pas supprimer une branche encore nécessaire.
- Ne pas rebaser ni modifier automatiquement les autres PR ou branches
  indépendantes après une fusion : cela crée du bruit et des notifications
  inutiles. Le traitement des PR empilées directement dépendantes est la seule
  exception à ce nettoyage ciblé, sauf demande explicite de l'humain.

## Séparation entre code et exploitation

Ce dépôt public contient le code et les instructions de développement local.
Les destinations, configurations et procédures propres aux environnements
restent dans les dépôts privés de déploiement. Ne pas inscrire ici de secrets,
d’accès serveur ou de consigne imposant une infrastructure particulière.

## Descriptions des pull requests

Avant de créer ou de modifier une description de PR, lire le modèle commun :
https://github.com/eures-beta/.github/blob/main/pull_request_template.md

Cette lecture est obligatoire, y compris avec la CLI ou l’API GitHub : le modèle
hérité n’est pas présent dans le clone local. Rédiger en français, conserver les
rubriques pertinentes et remplacer les textes d’aide par le pourquoi, le comment
et les instructions de test propres à la PR. Les sections indiquées comme
optionnelles peuvent être omises si elles ne s’appliquent pas.

Distinguer les tests exécutés de ceux restant à faire ; ne cocher que les
vérifications réalisées. Si le modèle est inaccessible, le signaler et utiliser
les rubriques Pourquoi, Comment, À vérifier et Comment tester, sans inventer
son contenu. Ne pas recopier le modèle dans ce dépôt : GitHub utilise le modèle
commun en l’absence de modèle local.
