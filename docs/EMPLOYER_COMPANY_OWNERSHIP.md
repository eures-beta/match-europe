# Rattachement employeur à un établissement — recette locale

## Périmètre

Lot 2, PR nº 19 empilée sur la PR nº 18 (`codex/employer-email-account`).
Un compte individuel peut appartenir à plusieurs établissements. Les membres actifs
d’un établissement partagent ses imports d’offres ; le créateur est conservé.
Aucune appartenance n’est déduite de l’email, du domaine ou du nom d’établissement.
Les droits conseiller/admin existants restent distincts. Le matching fictif `Offer`
et ses conversations ne sont pas modifiés.

## Parcours simplifié

Activer `ME_EMPLOYER_LOCAL_API=1`, `ME_EMPLOYER_EMAIL_LOCAL=1` et
`ME_LOCAL_REVIEW_ONLY=1`, en démonstration et sur loopback uniquement.

1. Importer une offre fictive, la relire puis renseigner le contact.
2. La soumission conserve le brouillon et conduit à la connexion. Aucun envoi
   AGLAE ni géocodage n’est déclenché par cette soumission dans ce mode.
3. Utiliser l’email simulé. Le lien à usage unique porte uniquement le brouillon
   soumis depuis ce navigateur ; aucun identifiant arbitraire n’est accepté.
4. La vérification réserve le brouillon à une identité durable. Rotation de
   session, ouverture du lien sur un autre navigateur et reconnexion après
   déconnexion conservent cet accès, même avant le choix de l’établissement.
5. Un seul établissement : afficher son nom et « Enregistrer l’offre pour cet
   établissement ». Plusieurs : choisir explicitement l’établissement concerné.
   Aucun : saisir uniquement son nom, prérempli avec le nom extrait si disponible.
6. Après rattachement, une appartenance active est nécessaire pour lire ou modifier
   l’import. L’ancien navigateur anonyme perd l’accès. Le retrait d’une appartenance
   retire les droits dès la requête suivante, y compris pour le créateur.

La création d’un autre établissement est refusée côté serveur lorsqu’une
appartenance active existe. Le verrou sur l’identité sérialise le premier
rattachement entre navigateurs. Une révision périmée est refusée pour éviter
l’écrasement silencieux des corrections faites par deux collègues.

## Données et limites

Migration additive `0006` uniquement : identités, établissements, appartenances,
références du propriétaire/créateur et brouillon porté par le lien. Le modèle
`EmployerCompany` conserve son nom technique mais représente l’établissement.
Aucune migration d’identification officielle ni de rapprochement des données.
Les anciens imports non attribués conservent leur accès par session.

L’établissement n’est identifié que par son nom dans cette première version.
Des homonymes sont possibles : ils ne sont jamais fusionnés ni partagés par
simple correspondance de nom. Identité juridique, vérification du mandat et
traitement des doublons restent à concevoir avant production.

Les invitations et la révocation par interface restent un lot séparé ; les tests
créent explicitement des appartenances fictives. Pas de nouvelle page « Mes offres »
dans ce lot. Aucun email réel, habilitation de production, merge ou déploiement.
Les formulaires utilisent POST/CSRF, des libellés explicites et les textes FR/EN/DE
dans la coque V2 existante. Aucun logo ni lecteur PDF modifié.

Référence de conception : [Company / CompanyMembership des Emplois de
l’inclusion](https://github.com/gip-inclusion/les-emplois/blob/main/itou/companies/models.py).
Aucun code tiers copié ; leurs parcours complets ne sont pas reproduits.

## Validation de la branche destinée à la PR

81 tests PostgreSQL passent sur la version isolée de cette PR, dont onze tests de
rattachement : partage et retrait des droits, reconnexion autre navigateur,
conservation du brouillon, premier nom obligatoire, refus de création supplémentaire,
choix multiple obligatoire et absence de droits par homonymie. Contrôle Django sans
erreur, migrations cohérentes, traductions compilées et diff vérifié.
Le parcours simplifié a aussi été contrôlé visuellement dans la recette locale
intégrée ; ce contrôle ne vaut pas audit complet d’accessibilité ou de marque.
