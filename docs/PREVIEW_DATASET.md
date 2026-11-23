# Jeu fictif des recettes jetables

`make test-accounts-seed` prépare des parcours reliés. Huit identités sont créées
sur une base neuve, dont cinq proposées dans le sélecteur. L'ancien second employeur
est supprimé après transfert de ses données utiles. Aucun modèle ni migration ajouté.

## Couverture d’une base fraîche

Mesure PostgreSQL du petit jeu historique et du jeu complet. Les essais réalisés
ensuite changent ces nombres. Les tables intermédiaires automatiques sont exclues.

| Modèle | Avant | Après |
| --- | ---: | ---: |
| User | 8 | 8 |
| CandidateProfile | 5 | 5 |
| EmployerProfile | 0 | 1 |
| JobOffer | 3 | 16 |
| CandidateOfferMatch | 5 | 18 |
| MatchEvaluation | 5 | 18 |
| MatchDecision | 1 | 14 |
| CandidateOfferReview | 1 | 13 |
| CandidateOfferReviewAnswer | 13 | 169 |
| CandidateOfferReviewEvent | 0 | 27 |
| CandidateProfileSharing (8 accords, 4 refus) | 0 | 12 |
| CandidateOfferConversation | 0 | 5 |
| CandidateOfferConversationMessage | 0 | 6 |
| CandidateSupport | 0 | 5 |
| JobOfferSupport | 0 | 16 |
| CandidateProfileReviewSuggestion | 0 | 2 |
| CandidatePushSubscription | 0 | 2 |
| Invitation | 0 | 3 |
| OccupationSkillSuggestion | 0 | 2 |
| Session | 0 | 2 |
| LoginRateLimit | 0 | 2 |
| LogEntry | 0 | 2 |
| Group | 2 | 2 |
| Permission | 104 | 104 |
| ContentType | 26 | 26 |

Les 25 modèles actifs sont peuplés, contre 10 auparavant.
Le [README des exemples](../eures_beta/users/preview_data/) explique la répartition
par compte, offre et revue, les métiers et le calcul des totaux.

## Parcours

Les treize offres supplémentaires portent un titre « Offre fictive ». Elles sont
possédées par le même employeur. Les deux candidats du sélecteur disposent
chacun de propositions et d’une conversation ouverte avec trois messages,
attribués au conseiller, au candidat et à l’employeur correspondant.

Les cas couvrent un rapprochement refusé, une revue close, des réponses prêtes
à examiner, une prise en charge, une demande de précision, puis des invitations
à converser demandées, acceptées, ouvertes et refusées. Trois offres avec des
conditions horaires et salariales refusées déclenchent deux suggestions de
réexamen des préférences, via les services métier existants.

Le conseiller trouve des échéances passées, du jour et à venir pour les cinq
candidats, ainsi que des offres suivies ou sorties du suivi. Les invitations
illustrent attente, expiration et acceptation. L'employeur a ses pratiques de réponse
renseignées. Les profils personnels différents déjà saisis sur deux anciens comptes
sont conservés sans écrasement ; voir [la consolidation](TEST_ACCOUNTS.md).

## Conservation et limites

Les UUID des offres sont déterministes. Une transaction et les garde-fous des
[comptes fictifs](TEST_ACCOUNTS.md) protègent le peuplement. Un rapprochement déjà
calculé, décidé ou doté d’une revue n’est plus avancé automatiquement : les essais
de l’utilisateur sont conservés. Les créations utilisent les services métier
pour calculs, décisions, réponses, accords et historique des revues.

- Les deux abonnements Push appartiennent aux candidats hors sélecteur, avec des
  destinations `.invalid` rejetées par le transport. Ils ne représentent pas un
  consentement du navigateur ni une livraison effective.
- Deux sessions de confirmation ne contiennent aucune identité authentifiée.
  Leur expiration suit la durée de confirmation de l’application.
- Deux compteurs anti-abus expirés ne bloquent aucun compte.
- Deux entrées administratives décrivent explicitement l’initialisation fictive.
- Deux suggestions de compétences viennent de relations officielles du catalogue,
  avec une provenance de fixture distincte du cache Albert.
- Les dates d’envoi des invitations sont fictives : aucun message n’a été envoyé.

Le nettoyage normal peut retirer sessions et compteurs. Une page étrangère au
rôle connecté reste inaccessible. Albert, les e-mails, Push et l’import d’un vrai
PDF restent à tester séparément. Les textes des exemples sont français ; les
interfaces conservent leurs traductions FR/EN/DE.

## Commandes et code

`make test-accounts-seed SEED_ARGS=--report` compte les lignes sans modifier la
base. `SEED_ARGS=--minimal` conserve le petit jeu pour les tests ciblés ; les
recettes utilisent le jeu complet par défaut.

Code : [users/preview_data](../eures_beta/users/preview_data/).
`make test TESTS=tests.users.test_preview_data` vérifie les 25 modèles, liens,
états, parcours des comptes, refus, absence d’appels externes et relance à
données identiques.
