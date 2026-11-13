# Confirmations candidat par offre

## Modèles et relations

- `CandidateOfferMatch` représente le rapprochement unique candidat–offre.
- `CandidateOfferReview` représente l’examen de cette offre par le candidat,
  ouvert par un conseiller : zéro ou un examen par rapprochement.
- `CandidateOfferReviewAnswer` conserve les réponses aux questions et leurs
  versions : plusieurs réponses par examen.
- `CandidateProfileSharing` conserve les choix successifs d’autoriser ou refuser
  le partage du profil avec l’employeur de cette offre. Il ne signifie pas que
  le partage a effectivement eu lieu.

L’accès inverse depuis le rapprochement est `candidate_offer_review`. Les champs
de relation `pair` et `request`, ainsi que `answers` et `agreements`, gardent leur
structure et les mêmes identifiants. Les routes publiques restent identiques.

La migration `matching.0006_candidate_offer_model_names` renomme les quatre
modèles dans l’état Django et conserve les tables physiques historiques
`matching_matchpair`, `matching_confirmationrequest`, `matching_confirmationanswer`
et `matching_transmissionagreement`. Elle conserve aussi les identifiants des types
de contenu et permissions administratives, en actualisant leurs noms ; aucune
permission supplémentaire n’est requise pour les actions des conseillers.
Des métadonnées concurrentes incompatibles provoquent un refus explicite.

Les migrations déjà publiées et les fixtures qui représentent un ancien schéma
gardent leurs anciens noms : ne pas les réécrire. Le retour arrière restaure les
noms précédents sans supprimer les réponses, choix, relations ou dates.

## Fonctionnement

La PR #162 s’appuie sur les paires candidat–offre du matching. Le portefeuille
d’équipe et son modèle de données (#161) sont reportés.

Tout conseiller connecté et actif peut ouvrir le détail d’une paire
éligible, demander une confirmation et lire le récapitulatif. Tous les
conseillers ont les mêmes droits, sans permission Django supplémentaire.
Une demande apparaît dans l’espace
privé du candidat propriétaire. Elle porte sur un profil vérifié et une offre
validée. La perte de l’éligibilité de la paire ferme cet accès.

Le candidat répond pour cette offre, y compris lorsque son profil paraît
compatible. Les créneaux sont indépendants. Les informations manquantes côté
employeur restent à clarifier avec l’employeur. Les réserves et les refus ne
modifient pas le profil ni la décision de matching. Un changement général
renvoie vers l’édition du profil, que le candidat valide séparément.

L’autorisation de transmission est recueillie séparément et peut être retirée.
Elle devient périmée si les réponses ou les informations pertinentes changent.
La sollicitation et l’accord ne déclenchent aucun envoi ni accès employeur.
Les pages sont privées et les formulaires protègent contre les réponses périmées.

La migration `matching.0005_offer_confirmations` crée les demandes, réponses et
accords sur une installation vierge. Elle reconnaît aussi l’ancienne migration
`0003_confirmationrequest_confirmationanswer_and_more`, déjà exécutée dans
certaines recettes avant le réagencement de la pile.

Dans ce cas, elle vérifie les trois tables : colonnes et types, nullabilité,
identités et valeurs par défaut, clés primaires, unicité, clés étrangères et
index. Si le schéma correspond, Django conserve les tables, leurs données,
identifiants et séquences, puis enregistre normalement la nouvelle migration.
L’ancien enregistrement est conservé. Aucun `--fake` ni effacement n’est requis.
Un schéma partiel, incompatible ou sans cet historique précis est refusé.

Le retour arrière d’une migration ayant repris le schéma historique conserve
ces tables et leur ancien historique ; une installation neuve conserve le retour
arrière habituel avec suppression des trois tables nouvellement créées.

`make confirmations-migrations-test` reproduit l’ancien schéma à partir de sa
migration figée, avec des données non vides. Il vérifie leur conservation,
l’aller-retour, les séquences, la création vierge et le refus des divergences.

Utiliser `make confirmations-test` pour les tests ciblés, `make test` pour
la suite PostgreSQL et `make check` pour les contrôles Django et de migration.
