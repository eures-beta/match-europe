# Offres du compte employeur

Le tableau de bord liste les offres du compte employeur connecté, avec intitulé,
nom d’entreprise déclaré, lieu et dernière modification. La pagination porte sur
25 offres. Les liens de retour émettent directement `/accounts/dashboard/`.
`/employer/offers/` redirige temporairement vers cette adresse selon
[la politique de retrait à 30 jours](LEGACY_ROUTES.md).
Le détail, la modification et la duplication ne sont accessibles qu’au créateur.
Voir [le contrat de propriété](EMPLOYER_OFFER_OWNERSHIP.md).

## Consultation et modification

Le détail présente les champs métier et un contact conseiller distinct du compte.
Le formulaire conserve les métadonnées de source et les questions déjà enregistrées.
Le nom d’entreprise est un texte descriptif, sans structure ou droit associé.
La sauvegarde ne publie pas l’offre sur un service externe ; elle programme le
matching des offres éligibles après validation de la transaction.

L’offre reste modifiable tant que `search_started_at` n’est pas renseigné.
Un enregistrement, une préparation ou une validation ne déduit pas ce démarrage.
Les actions d’écriture de l’API et de l’éditeur contrôlent ce verrou côté serveur.
Une révision périmée empêche l’écrasement d’une modification faite dans un autre
onglet ou navigateur. Annuler quitte le formulaire sans sauvegarder les changements.

## Duplication

Une action POST avec CSRF et révision actuelle crée un brouillon appartenant au
même compte, avec un nouvel UUID et un lien vers l’original. Données métier,
conditions structurées et contact sont copiés. Dates de validation/envoi/recherche,
réponses externes, géolocalisation, URL source et attribution conseiller ne sont
pas repris. L’original reste inchangé. Annuler le formulaire de copie ne supprime
pas le brouillon déjà créé.

## Contrôles

Rôle actif, propriété, méthode HTTP, CSRF et révision sont revérifiés à chaque
requête. Le nom ou l’email de contact ne donne aucun accès à un autre compte.
Les anciens rattachements et choix d’établissement sont supprimés ; leurs
adresses historiques répondent 410 sans attribuer ou déplacer une offre.
Les mêmes protections s’appliquent en local, recette et production.

Les écrans utilisent les templates communs, les labels traduits FR/EN/DE et les
composants accessibles du design system. `make test TESTS=tests.employers` vérifie
consultation, édition, copie, conflit, verrouillage et refus d’accès entre comptes.
