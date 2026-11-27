# Reprise du projet

Dépôt conseiller avec compte employeur propriétaire, précréé actif si nécessaire :
[parcours et vérifications](docs/ADVISER_OFFER_DEPOSIT.md), confirmation téléphonique suffisante.

La consultation des offres employeur livrée par #242 inclut toutes les offres
enregistrées et leur détail en lecture seule, indépendamment de leur éligibilité
au matching. Voir [le contrat](docs/ADVISER_EMPLOYER_OFFERS.md).

Vérifier GitHub, les CI et l'environnement avant toute opération : ce document
ne prouve aucun déploiement et n'autorise aucune fusion.

## Invitation candidat

Objet EURES et introduction contextualisée FR/EN/DE, salutation sans prénom.
Identité et structure du conseiller reprises du compte, replis sans identité
inventée ; liens, notice et logos conservés. La relance reste inchangée.

## À lire pour reprendre

- [Vue d'ensemble](docs/VUE_ENSEMBLE.md) : rôles, domaines et parcours.
- [Décisions actuelles](docs/DECISIONS.md) : contrats validés et raisons.
- [Retours récurrents](docs/AGENT_FEEDBACK.md) : erreurs à ne pas reproduire.
- [Guide des agents](docs/AGENT_WORKFLOW.md) : procédures ciblées et fin de tâche.
- [Documentation](docs/DOCUMENTATION.md) : budgets, entretien et historique Git.

## Matching au dépôt du profil candidat

`codex/candidate-profile-matching` est empilée sur #243 : création du profil vérifié
et modification confirmée déclenchent le calcul après commit sur les offres existantes.
Décisions du conseiller et consentements conservés ; aucun rattrapage global des
anciens profils. Calcul synchrone, sans relance automatique en cas d’erreur.

## Travail en revue

La pile contient des changements encore non fusionnés : ne pas les présenter
comme déjà déployés. Son ordre et ses SHA sont des informations GitHub périssables,
pas une liste à dupliquer dans ce fichier.

- [#203](https://github.com/eures-beta/match-europe/pull/203) : design system Bootstrap/ECL.
- [#209](https://github.com/eures-beta/match-europe/pull/209) : validation CI interne
  portée par push ; les jobs pull_request ignorés ne remplacent pas cette preuve.
- [#211](https://github.com/eures-beta/match-europe/pull/211) : CSS web externe et lint.
- [#216](https://github.com/eures-beta/match-europe/pull/216) : noms Push neutres,
  nouveau contexte VAPID et renouvellement des abonnements existants autorisés.
- [#226](https://github.com/eures-beta/match-europe/pull/226) : noms des modèles,
  relations et objets PostgreSQL, avec migrations réversibles et données conservées.
- [#228](https://github.com/eures-beta/match-europe/pull/228) : maintenance Python ;
  [#229](https://github.com/eures-beta/match-europe/pull/229) et
  [#230](https://github.com/eures-beta/match-europe/pull/230) : recherches bornées
  et outillage de triage CodeQL.

- Harmonisation des modèles : 11 tables, relations, contraintes et objets SQL
  renommés en place ; [guide et retour arrière](docs/MODEL_NAMING.md).
  Prévoir les verrous DDL au déploiement ; conserver les migrations historiques.

Retirer les entrées après intégration et mise à jour des guides concernés.
N'ajouter ici que ce qui change concrètement la prochaine reprise.

## Points à vérifier selon la tâche

- Python : [maintenance hebdomadaire](docs/PYTHON_RUNTIME.md) en revue ; activation
  sur main et autorisation GitHub Actions de créer des PR à vérifier après fusion.
- CodeQL : [triage des alertes initiales](docs/CODEQL_TRIAGE.md), corrections
  d'extraction et protections démontrées. Vérifier le scan de la branche ; une PR
  non fusionnée n'est pas une résolution sur `main`.
- Migration : données existantes, relations, ContentTypes et permissions conservés,
  aller-retour testé quand applicable ; pas de réécriture d'une migration publiée.
- Push : réception et reprise sur les téléphones ciblés à vérifier manuellement.
  Le modèle garde actuellement un seul abonnement par profil.
  Le changement de contexte VAPID change la clé ; préserver le renouvellement décrit
  dans [le guide Push](docs/CANDIDATE_PUSH.md), pas un remplacement textuel aveugle.
- Albert : clé et sources officielles préparées pour les appels réels ; les tests
  utilisent une frontière simulée. Un test simulé ne prouve pas la disponibilité externe.
- Production/recette : configuration et secrets dans les dépôts privés.
  Vérifier le réglage effectif `DEMO_ACCOUNTS_ENABLED` et les protections de la
  base fictive avant de promettre une recette peuplée. Une mise à jour du
  contrôleur ne reconfigure pas automatiquement les anciennes recettes.
- Suppression automatique selon les durées annoncées et revue juridique complète :
  vérifier les capacités réellement implémentées dans [la notice](docs/DATA_PROTECTION.md).
  Ne pas annoncer une purge effective sur la seule présence d'une durée dans un texte.

## Historique

Les anciens comptes rendus, variantes abandonnées et preuves de validation restent
dans [l'historique Git de ce fichier](https://github.com/eures-beta/match-europe/commits/main/HANDOFF.md)
et dans les PR citées. Aucun fichier d'archives n'est nécessaire.

Catalogue métiers/compétences candidat et employeur : [contrat et validations](docs/COMMON_OCCUPATION_SKILLS.md). PR en préparation, sans fusion ni déploiement.

Suite locale de #253 : clôture Albert et traitement partagé des dossiers.
Voir [contrat et recette](docs/REVIEW_HANDOFF.md). Publication et recette 7 jours demandées.

## Suite de la PR 290

La branche `codex/employer-shared-conversation` raccorde l’accord employeur
au fil à trois : ouverture par le conseiller avec les deux accords actuels,
sans nouvelle demande candidat. Aucun changement de schéma supplémentaire.
Les vérifications et limites de publication sont décrites dans la PR descendante.
