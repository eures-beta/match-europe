# Reprise du projet

La consultation des offres employeur livrée par #242 inclut toutes les offres
enregistrées et leur détail en lecture seule, indépendamment de leur éligibilité
au matching. Voir [le contrat](docs/ADVISER_EMPLOYER_OFFERS.md).

État documentaire du sommet de la pile au 16 novembre 2026, pas une preuve de
déploiement ni un mandat de fusion. Vérifier GitHub et l'environnement concerné
avant toute opération. Les résultats de CI sont sur chaque PR ; aucun compteur
historique de tests n'est à entretenir ici.

## À lire pour reprendre

- [Vue d'ensemble](docs/VUE_ENSEMBLE.md) : rôles, domaines et parcours.
- [Décisions actuelles](docs/DECISIONS.md) : contrats validés et raisons.
- [Retours récurrents](docs/AGENT_FEEDBACK.md) : erreurs à ne pas reproduire.
- [Guide des agents](docs/AGENT_WORKFLOW.md) : procédures ciblées et fin de tâche.
- [Documentation](docs/DOCUMENTATION.md) : budgets, entretien et historique Git.

## Travail en revue

La pile contient des changements encore non fusionnés : ne pas les présenter
comme déjà déployés. Son ordre et ses SHA sont des informations GitHub périssables,
pas une liste à dupliquer dans ce fichier.

- [#193](https://github.com/eures-beta/match-europe/pull/193) et
  [#197](https://github.com/eures-beta/match-europe/pull/197) : profil PWA, suivi
  conseiller, avis Albert et conversation à trois. Ne pas confondre revue par
  offre et conversation réelle ; consulter les limites de leurs descriptions.
- [#195](https://github.com/eures-beta/match-europe/pull/195) : retrait de trois
  modèles employeur hérités ; préserver l'historique des migrations.
- [#196](https://github.com/eures-beta/match-europe/pull/196),
  [#199](https://github.com/eures-beta/match-europe/pull/199),
  [#200](https://github.com/eures-beta/match-europe/pull/200) :
  commandes de tests paramétrées, serveur unique et tests dans `tests/`.
- [#202](https://github.com/eures-beta/match-europe/pull/202) : couche web `www`.
- [#203](https://github.com/eures-beta/match-europe/pull/203) : design system Bootstrap/ECL.
- [#204](https://github.com/eures-beta/match-europe/pull/204) et
  [#208](https://github.com/eures-beta/match-europe/pull/208) : routes explicites
  et compatibilité des anciennes adresses.
- [#206](https://github.com/eures-beta/match-europe/pull/206) et
  [#207](https://github.com/eures-beta/match-europe/pull/207) :
  simplification des réglages et politique de connexions PostgreSQL commune.
- [#209](https://github.com/eures-beta/match-europe/pull/209) : validation CI interne
  portée par push ; les jobs pull_request ignorés ne remplacent pas cette preuve.
- [#211](https://github.com/eures-beta/match-europe/pull/211) : CSS web externe et lint.
- [#216](https://github.com/eures-beta/match-europe/pull/216) : noms Push neutres,
  nouveau contexte VAPID et renouvellement des abonnements existants autorisés.

Retirer les entrées après intégration et mise à jour des guides concernés.
N'ajouter ici que ce qui change concrètement la prochaine reprise.

## Points à vérifier selon la tâche

- Migration : données existantes, relations, ContentTypes et permissions conservés,
  aller-retour testé quand applicable ; pas de réécriture d'une migration publiée.
- Push : réception et reprise sur les téléphones ciblés à vérifier manuellement.
  Le modèle garde actuellement un seul abonnement par profil.
  Le changement de contexte VAPID change la clé ; préserver le renouvellement décrit
  dans [le guide Push](docs/CANDIDATE_PUSH.md), pas un remplacement textuel aveugle.
- Albert : clé et sources officielles préparées pour les appels réels ; les tests
  utilisent une frontière simulée. Un test simulé ne prouve pas la disponibilité externe.
- Production/recette : configuration et secrets dans les dépôts privés.
  [#27 privé](https://github.com/eures-beta/match-europe-deploy-clever/pull/27)
  accompagne le réglage `DEMO_ACCOUNTS_ENABLED` de
  [#191](https://github.com/eures-beta/match-europe/pull/191) ; vérifier sa livraison
  avant de promettre une recette peuplée.
- Suppression automatique selon les durées annoncées et revue juridique complète :
  vérifier les capacités réellement implémentées dans [la notice](docs/DATA_PROTECTION.md).
  Ne pas annoncer une purge effective sur la seule présence d'une durée dans un texte.

## Historique

Les anciens comptes rendus, variantes abandonnées et preuves de validation restent
dans [l'historique Git de ce fichier](https://github.com/eures-beta/match-europe/commits/main/HANDOFF.md)
et dans les PR citées. Aucun fichier d'archives n'est nécessaire.
