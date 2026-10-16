# Consignes de développement

## Pull requests et collaboration en équipe

### Création

- Créer une branche dédiée au travail demandé, avec le préfixe `codex/` sauf
  instruction contraire. La destination habituelle est `main`.
- Le titre de chaque pull request doit être entièrement choisi par l'humain.
  Demander explicitement à Eric de fournir le titre avant de créer la PR, sauf
  s'il l'a déjà donné. Ne pas générer de titre, même provisoire, ni se contenter
  de lui faire approuver un titre proposé par l'agent.
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

## URL de recette de référence

Décision validée par Eric le 16 octobre 2026 : les futurs développements de ce
dépôt ont pour destination de déploiement l'alpha FT :

https://matcheurope-alpha.beta.francetravail.fr/

Cette adresse est l'environnement partagé de développement et de validation,
et ne constitue pas une mise en production métier. Le squelette de ME#3 y a été
installé le 16 octobre 2026 ; les futurs déploiements doivent conserver ce domaine.

Après chaque déploiement, vérifier le contrôle `/health`, les pages concernées
et leurs fichiers statiques, puis indiquer la version déployée et le résultat des
contrôles. Prévoir un retour arrière avant de remplacer la version en service.

Cette destination de référence ne demande pas un déploiement automatique à
chaque modification et n'autorise pas à elle seule une fusion ou une modification
d'un autre environnement. Respecter le périmètre demandé pour chaque tâche.

Ne pas inscrire de secrets, d'accès serveur ou de procédures internes FT dans
ce dépôt public. Conserver les configurations et procédures de déploiement FT
dans l'espace privé approprié. Configurer les adresses d'environnement hors du
code applicatif, sans les coder en dur.
