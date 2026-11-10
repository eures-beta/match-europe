# Confirmations candidat par offre

La PR #162 s’appuie sur les paires candidat–offre du matching. Le portefeuille
d’équipe et son modèle de données (#161) sont reportés.

Un conseiller habilité à modifier les paires ouvre le détail d’une paire
éligible et demande une confirmation. Les conseillers habilités à consulter
les paires peuvent lire le récapitulatif. Une demande apparaît dans l’espace
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

La migration additive `matching.0005_offer_confirmations` crée les demandes,
réponses et accords au-dessus du schéma de `main`. Les aperçus ayant appliqué
les migrations de l’ancienne pile doivent être examinés séparément avant
réutilisation. La migration n’importe pas les données de cette pile.

Utiliser `make confirmations-test` pour les tests ciblés, `make test` pour
la suite PostgreSQL et `make check` pour les contrôles Django et de migration.
