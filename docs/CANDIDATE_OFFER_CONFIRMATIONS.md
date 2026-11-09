## Mise à jour — 9 novembre 2026

Les confirmations candidat fonctionnent dans tous les environnements, à distance et avec des adresses ordinaires. L’accès reste réservé au candidat propriétaire d’une demande rattachée à une équipe active avec ses affectations ; la révocation ferme cet accès. Les réponses et l’accord de transmission restent distincts, explicites, révocables et protégés contre les pages périmées. Les anciennes restrictions locales ci-dessous sont remplacées.

# Confirmations candidat par offre — recette locale

## Corrections après recette du 8 novembre 2026

Le résumé des erreurs affiche les libellés traduits et des liens vers les champs,
sans nom interne ni duplication des identifiants des messages locaux. La
modification d’une réponse reprend le choix et la précision courants ; une
confirmation périmée n’est pas préremplie. Les valeurs saisies restent conservées
en cas d’erreur et les protections contre les écrasements concurrents demeurent.

Vérifications : `make confirmations-test` (25 tests), `make test` (582 tests
PostgreSQL), `make check`, `make format-check`, `make format-html-check` et
`make translations-check` réussis. Extraction puis contrôle des traductions
également vérifiés dans une copie isolée. Navigateur : préremplissage, erreur
sans identifiant dupliqué et lien amenant le focus au champ vérifiés. Aucun
audit WCAG exhaustif, fusion, déploiement ni transmission réelle.

## Périmètre autorisé le 8 novembre 2026

Eric valide successivement les conditions déterminantes à confirmer même lorsque
le profil paraît compatible, leurs réponses possibles, le renouvellement ciblé,
les cas particuliers et deux moments : offre envisagée puis accord distinct avant
transmission. Il autorise ensuite leur implémentation. Base GitHub vérifiée : PR
#161 ouverte, commit `93b456655e41d2b0c449f916ca47d1ec3e498ee0`.
Branche `codex/candidate-offer-confirmations`. Pas de fusion ni de déploiement.

Ce lot est un dialogue guidé déterministe dans Django, sans appel au service
Albert réel, sans interprétation automatique des réponses libres et sans PWA
nouvelle. La transmission elle-même n’existe pas : l’accord est seulement enregistré.
Le calcul, les poids et les décisions de matching restent inchangés. Une réponse
n’ajoute pas de compétence acquise et ne produit aucun rejet automatique.

## Parcours

1. Un conseiller avec droit de décision ouvre une paire de son équipe et choisit
   « Faire confirmer cette offre par le candidat ». L’offre devient visible pour
   ce seul candidat dans son espace privé. Aucune notification n’est envoyée.
2. Depuis son profil, le candidat ouvre « Offres à confirmer ». Poste, employeur,
   lieu et conditions connues sont présentés. Les textes d’offre sont affichés
   sans interprétation ; aucun horaire exact ou fréquence n’est inventé.
3. Une question à la fois : écarts bloquants ou incompatibilités d’abord, inconnus
   utiles ensuite, puis conditions déjà compatibles. Les exigences manquantes
   restent côté employeur, sans question artificielle au candidat.
4. Chaque créneau exigé a sa réponse indépendante. Les compétences sont des
   déclarations, pas des certifications ; apprendre n’est pas maîtriser.
5. Le récapitulatif distingue confirmations, réserves, refus pour cette offre,
   changements généraux et demandes de précision. Les textes ambigus restent
   des réserves à examiner par une personne ; aucune conversion par un modèle IA.
6. Une correction générale ouvre la relecture du profil existante. Le texte de
   correction reste une note : il n’est pas converti automatiquement en champs.
   Le candidat modifie et valide séparément le profil. Une exception pour une
   offre ne modifie jamais la préférence générale.
7. Après les réponses aux questions disponibles, un choix explicite distinct
   enregistre l’accord ou le refus de transmission à cet employeur pour cette
   offre. Les réserves et les manques côté employeur restent visibles même si
   l’accord est donné ; cet accord ne prouve pas la compatibilité et ne déclenche
   ni envoi ni accès employeur.

## Données, renouvellement et accès

Migration additive `matching.0003` : `ConfirmationRequest`, `ConfirmationAnswer`,
`TransmissionAgreement`. Événements avec auteur authentifié et date, conditions
structurées présentées, réponse, note éventuelle et empreinte. Aucun secret de
connexion copié dans ces événements. Admin : métadonnées seules, lecture seule.

Chaque question est liée aux données candidat et offre qui la concernent ;
les autres confirmations restent valables. Une nouvelle exigence reçoit une
nouvelle question, une exigence retirée sort du récapitulatif courant sans effacer
l’historique. Les disponibilités sont reconfirmées à un nouveau jour, car il
n’existe pas de date de déclaration par champ. Le nom du poste, l’employeur et
le lieu font partie du contexte présenté. Toute modification du contenu de l’offre,
du profil ou des réponses invalide l’accord de transmission ; la simple consultation
ne crée rien. Un nouveau numéro de révision technique sans changement de contenu
n’invalide pas à lui seul une confirmation.

Les textes libres non structurés ne sont pas décomposés en critères : leur modification
invalide l’accord de transmission, mais ne génère pas automatiquement de nouvelles
questions précises. Le conseiller doit clarifier/structurer ces conditions. Plusieurs
métiers alternatifs d’une offre ne deviennent pas des exigences cumulatives.

Verrous de paire, demande, profil et offre ; contrôles d’empreinte et de version
d’événement contre les formulaires périmés. Double clic identique idempotent.
Une ancienne page ne peut pas remplacer silencieusement un refus plus récent.

Gardes locales existantes conservées : loopback, mode équipe et matching local,
aucun email réel, comptes `.invalid` actifs, profil confirmé et offre validée.
Accès candidat limité au propriétaire ; accès conseiller limité à l’équipe active,
à ses attributions actuelles et au droit de décision pour solliciter. Révocation
d’attribution ou désactivation : accès fermé. GET sans écriture, POST avec CSRF,
réponses privées sans cache. Ni superutilisateur ni rôle employeur ne donne un
accès implicite aux confirmations.

Pas de conservation durable ni purge automatique définie : base de recette
jetable uniquement. Avant une utilisation réelle, définir la rétention, les droits
de transmission et l’intégration effective au service Albert dans un autre lot.

## Essayer

Environnement Python et PostgreSQL propres au worktree ; voir `LOCAL_MATCHING.md`.
Une autre instance utilise déjà 55441 sur le poste de recette : cette branche
emploie sa propre instance sur 55442, base `albert_confirmations_20261108`.
`make matching-db-init`, puis `make matching-db-start MATCHING_DB_PORT=55442` ;
configurer le même port dans le `.env` local. Ne pas arrêter une autre instance.

- `make install-test`, `make install-quality` : dépendances isolées.
- `make db-create`, `make migrate` : base jetable et migration additive.
- `make matching-translations`, `make confirmations-seed` : langues et comptes fictifs.
- `make confirmations-run` : recette sur le port 9043, jamais exposée au réseau.
- Entrée `/accounts/test-accounts/` : conseiller de test, candidat A, demande de
  confirmation ; changer ensuite vers « Candidat de test — confirmations des offres ».
- Candidat : profil → offres à confirmer → offre → réponses → accord distinct.
- `make confirmations-test` : tests ciblés ; `make test` : suite PostgreSQL complète.
- `make check`, `make translations-check`, `make format-check`,
  `make format-html-check` : contrôles de cohérence.

## Vérifications de ce lot

22 tests ciblés et 579 tests PostgreSQL complets réussis ; Django et absence de
migration oubliée contrôlés. Contrôles de langue, Black, format et structure HTML réussis. Parcours navigateur
conseiller/candidat et réserve sur le samedi matin vérifiés ; largeur mobile
390 px sans débordement horizontal. Audit WCAG exhaustif, service Albert
réel, PWA et mise en relation externe exclus de cette vérification.
