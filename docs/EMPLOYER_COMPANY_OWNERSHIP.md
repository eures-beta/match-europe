# Rattachement employeur et espace entreprise — recette locale

## Périmètre

Lot 2, sur une branche dédiée issue de `codex/employer-email-account` (point 1,
PR nº 18). Vérification GitHub du 22 octobre 2026 : la PR nº 18 est en
brouillon, de `codex/employer-email-account` vers `codex/employer-offer-creation`.
Ce lot cible `codex/employer-email-account` pour isoler son diff. Aucun merge ni
déploiement.

Le modèle sépare une identité individuelle vérifiée par email simulé, un espace
entreprise et une appartenance explicite active. Un import appartient à cet espace,
avec conservation de son créateur. Tous les membres actifs ont les mêmes droits
sur les imports de cet espace ; aucune appartenance n’est inférée du domaine email,
du contact de l’offre ou du nom de l’entreprise. Un membre peut appartenir à
plusieurs espaces. Une contrainte interdit les appartenances en double.

Référence examinée : [modèle Company / CompanyMembership des Emplois de
l’inclusion](https://github.com/gip-inclusion/les-emplois/blob/main/itou/companies/models.py)
et [documentation des collaborateurs](https://aide.emplois.inclusion.beta.gouv.fr/hc/fr/articles/16925342632593).
Cette référence confirme le principe utilisateurs / structure / appartenance.
Aucun code tiers n’a été copié. Les droits et parcours complets de cette application
ne sont pas reproduits.

## Parcours

Activer `ME_EMPLOYER_LOCAL_API=1`, `ME_EMPLOYER_EMAIL_LOCAL=1` et
`ME_LOCAL_REVIEW_ONLY=1`, en démonstration, sur loopback uniquement.

1. Importer, relire et corriger une offre avec des données fictives.
2. La soumission du contact enregistre le brouillon et conduit à la connexion.
   Aucun envoi AGLAE ou géocodage n’est déclenché par cette soumission dans ce mode.
3. Demander un lien avec une adresse individuelle fictive, puis utiliser l’email simulé.
   Le lien porte uniquement le dernier brouillon soumis dans ce navigateur ; le
   client ne peut pas choisir un identifiant arbitraire à rattacher.
4. La vérification réserve ce brouillon à l’identité durable. La rotation de session,
   un lien ouvert dans un autre navigateur et une reconnexion après déconnexion
   conservent cet accès. Aucun ancien import n’est récupéré par son email.
5. Choisir explicitement l’un de ses espaces actifs, ou créer un nouvel espace nommé.
   Créer un espace ne prouve ni l’identité juridique ni le mandat de l’entreprise.
6. Après rattachement, seule une appartenance active donne accès par les routes
   locales d’import. L’ancien navigateur anonyme perd l’accès. Retirer l’appartenance
   retire les droits dès la requête suivante, y compris pour le créateur.

Les enregistrements historiques sans propriétaire conservent leurs droits par
session ; aucune migration automatique de leurs droits n’est effectuée.
Les droits conseiller et admin existants restent distincts. Les modèles de matching
fictifs `Offer` et leurs conversations ne sont pas migrés dans ce lot.

## Limites

L’ajout, l’invitation et la révocation par interface restent un lot séparé.
Pour les tests, les appartenances sont créées explicitement avec des identités
fictives ; aucun mécanisme public de revendication d’une entreprise n’est ajouté.
Le nom d’espace n’est pas un identifiant juridique et n’est pas unique : deux noms
identiques ne fusionnent jamais leurs données. Identification des établissements,
validation du premier représentant et dédoublonnage restent à concevoir avant production.

Pas de nouvelle page « Mes offres » dans ce lot. Les routes et la prévisualisation
existantes permettent la vérification des accès et de la révision concurrente.
La page d’accueil minimale confirme le rattachement, sans tableau de bord.
Le verrou et la révision existants empêchent l’écrasement silencieux des corrections
faites par deux collègues. Les accès partagés restent limités à la recette locale ;
aucun email réel ni habilitation de production n’est validé.

Migration additive `0006` : identités, espaces, appartenances, références de
propriétaire/créateur et brouillon porté par le lien. Données, sessions et documents
restent hors Git. Les textes ajoutés existent en FR/EN/DE dans la coque V2 existante.

## Validation du 22 octobre 2026

77 tests PostgreSQL passent, dont sept nouveaux tests de rattachement : partage
lecture/écriture, conflit de révision entre collègues, retrait des droits,
reconnexion depuis un autre navigateur, isolation par entreprise, CSRF, FR/EN/DE,
conservation du brouillon avant et après rattachement. Contrôle Django sans erreur,
migrations cohérentes et syntaxe JavaScript vérifiée. Migration complète depuis une
base PostgreSQL jetable vide réussie. Parcours manuel dans le navigateur : texte
fictif → relecture → contact → email simulé → création d’espace → confirmation
réussi. Contrôle visuel de l’écran de rattachement dans la coque V2 ; ceci ne vaut
pas audit complet WCAG ni certification de marque.
