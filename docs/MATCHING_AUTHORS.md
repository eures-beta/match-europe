# Auteurs des décisions et des réponses

Tous les comptes sont des `User` dont le rôle exclusif et immuable est
`adviser`, `candidate` ou `employer`.

| Donnée | Auteur attendu |
| --- | --- |
| `MatchDecision.by_adviser` | Conseiller ayant pris la décision. |
| `CandidateOfferReview.requested_by_adviser` | Conseiller ayant demandé la revue. |
| Réponse `CandidateOfferReviewAnswer` | Candidat du profil lié par `review.match.candidate.user`. |
| Accord `CandidateProfileSharing` | Même candidat, qui accepte ou refuse le partage. |
| `CandidateOfferConversationMessage.author` | Candidat, employeur ou conseiller participant à la conversation. |

Les réponses et accords ne stockent plus une deuxième identité candidat.
Leur auteur est déduit du profil ; `CandidateProfile.user` ne peut jamais être
réattribué, même à un autre compte candidat. Il n'y a pas de raccourci `actor`
conservé sans usage dans le code courant.

## Contrôles et migration

Les deux relations conseiller sont protégées par des déclencheurs PostgreSQL,
y compris pour `QuerySet.update`, `bulk_create` et SQL direct. Le profil exige
un compte candidat et interdit tout changement de propriétaire, au niveau modèle
et PostgreSQL. Le rôle du compte est déjà immuable en base. Les erreurs
d'intégrité ne sont pas absorbées ou converties en auteur inconnu.
Les autorisations des parcours exigent en plus un compte actif ; désactiver
un compte ne rend pas ses anciennes actions incohérentes.

La migration `candidates.0011` vérifie les rôles existants avant de protéger le
rattachement. `matching.0022` transforme les auteurs texte `adviser:<id>` en
relations vérifiées ; `local_operator` devient `NULL` (auteur historique inconnu).
Un texte inconnu, un conseiller inexistant ou d'un autre rôle, un demandeur de
revue non conseiller ou une réponse/un accord attribué à un autre compte que
le candidat bloque la migration transactionnelle. Aucune correction implicite.

Le retour arrière reconstruit `adviser:<id>`, `local_operator` et les deux anciennes
relations candidat à partir des comptes conservés. Les identifiants, dates,
réponses et consentements restent inchangés. `NULL` est réservé aux décisions
historiques : les nouvelles décisions exigent un conseiller identifié.

Ancien et nouveau code ne peuvent pas partager ce schéma pendant la bascule :
prévoir une fenêtre de migration. Aucun changement de configuration externe.

## Vérification

`make test TESTS=tests.matching.test_author_roles` vérifie les mauvais rôles,
écritures directes, réattributions, données contradictoires et l'aller-retour
sur des lignes non vides. La suite complète reste `make test`.

[Retour à la documentation](.)
