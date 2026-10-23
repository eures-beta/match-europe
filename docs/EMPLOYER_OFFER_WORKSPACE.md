# Espace employeur — retrouver, consulter, modifier et dupliquer les offres

## Périmètre du lot 3

Branche `codex/employer-offer-workspace`, basée sur la tête distante de la PR #20
vérifiée le 22 octobre 2026 : `ded96d92de6cddcf36694a9872775109763e39f8`.
Aucune modification de la branche de cette PR ni de la recette intégrée.
Code et ressources de développement dans le dépôt public ; aucune configuration
privée, donnée réelle ou procédure d’exploitation.

L’accueil connecté affiche directement les offres sous forme de tableau, avec
« Ajouter une offre » en tête et une zone « Mon compte » pour l’email et la
déconnexion. Les routes d’accueil et de liste utilisent le même écran.
Le tableau présente intitulé et lieu, établissement, état, dernière modification
et consultation. Paginé par vingt offres, il montre uniquement les établissements
avec appartenance active. Sur écran étroit, le défilement horizontal est limité
au tableau, accessible au clavier. Le rattachement sélectionné reste un encart
sur cet accueil ; aucun écran intermédiaire permanent.
Un filtre explicite est disponible si plusieurs établissements sont autorisés.
Les brouillons non rattachés restent dans un encart privé à leur créateur ; une
action POST permet de sélectionner le brouillon à rattacher sans en changer les droits.
Les anciens brouillons anonymes ne sont pas attribués automatiquement à un compte.

La consultation précède la modification. Le formulaire reprend les champs métier,
les précisions et les conditions de la V2, avec un contact conseiller distinct.
Les questions de préqualification masquées sont conservées sans nouvel écran.
L’enregistrement ne publie rien et ne déclenche aucune recherche ni appel externe.
Annuler quitte le formulaire sans enregistrer ses changements.

## Règle validée avec Eric

L’offre reste modifiable tant que la recherche de candidats n’a pas commencé.
Un enregistrement, une transmission de préparation ou une validation ne suffisent
pas à démontrer ce démarrage. Le champ serveur `search_started_at` est distinct
et n’est jamais pris depuis un formulaire, une URL ou un payload client.

La migration additive `0007_employer_offer_workspace` ajoute cette date et le lien
`duplicated_from`. Elle ne déduit aucun démarrage des anciennes dates et ne modifie
pas les données historiques. Dans le prototype actuel, aucun circuit ne déclenche
une véritable recherche pour ces imports. Le raccordement au démarrage confirmé
sera réalisé dans le lot suivant, avec gestion atomique du démarrage et des éditions
concurrentes ; les états inconnus d’un futur import réel devront être traités avant
ouverture, sans supposer automatiquement qu’ils sont modifiables.

Quand la date est renseignée, l’écran ne propose plus la modification. Tout POST
sur le nouvel éditeur et toutes les actions d’écriture de l’ancienne API locale
sont également refusés, y compris le changement de contact et la préparation.
Le modèle fictif historique `Offer` et ses résultats ne sont pas convertis.

Le prochain lot pourra présenter « Lancer ma recherche de candidats », avec
confirmation et verrouillage seulement après démarrage effectif confirmé.
Ce lot ne propose pas ce bouton et n’implémente pas la clôture.

## Duplication

Action POST et CSRF, sur une offre accessible et sa révision actuelle. Elle crée
immédiatement un nouveau brouillon, dans le même établissement, avec une nouvelle
identité technique et le créateur courant. Le lien vers l’original est conservé.
Les données métier et le contact sont copiés ; les réponses externes, dates de
validation/envoi/synchronisation/recherche, localisation calculée, URL source et
attribution conseiller ne sont pas repris. Aucun accès à un autre établissement
n’est créé. L’original reste inchangé, même quand sa recherche a commencé.

La copie est enregistrée dès la duplication. « Annuler » dans son formulaire ne
supprime pas ce nouveau brouillon ; cela annule seulement les changements du formulaire.
La suppression n’appartient pas à ce lot.

## Contrôles

Les appartenances actives sont revérifiées côté serveur sur chaque requête.
Le nom dans le texte de l’offre ne change ni l’établissement ni les habilitations.
Les conflits de révision bloquent l’écrasement du travail d’un collègue, conservent
la saisie affichée et invitent à ouvrir la version actuelle.
Une session expirée impose de se reconnecter ; aucun POST d’édition anonyme
n’enregistre de données. Les changements non enregistrés ne sont pas sauvegardés
automatiquement dans le navigateur ou dans les journaux.

FR/EN/DE, coques V2 et liens de langues conservant la page de travail. Libellés,
fieldset/legend, CSRF et focus visible. Le contrôle visuel ne vaut pas audit WCAG
complet ni certification de marque.

## Recette du 22 octobre 2026

99 tests PostgreSQL réussis, dont onze nouveaux : liste et filtre, isolation,
appartenance absente/révoquée, consultation/édition, contact invalide, conflits,
session expirée, verrouillage des nouvelles et anciennes routes, transmission
non assimilée au démarrage, duplication et remise à zéro, CSRF/POST, brouillons
privés, langues et pagination. Migration complète depuis une base jetable vide.

Parcours navigateur : connexion simulée, liste, consultation, modification et
confirmation, offre verrouillée sans bouton de modification, duplication puis
modification de la copie réussies. Données de recette fictives hors Git.

Serveur du lot 3 sur loopback 9020 avec base distincte ; les recettes 9018 et 9019
restent conservées. Trois modes locaux activés, aucun email réel ni appel externe.
Aucun push, changement de PR existante, merge ou déploiement dans cette étape.

Ajustement de recette demandé par Eric : accueil et liste réunis, tableau à la
place des cartes, établissement unique affiché sous le titre, compte repliable,
confirmation de rattachement conservée. Contrôle navigateur : compte et
déconnexion accessibles, aucun débordement horizontal du document sur écran
étroit, tableau avec en-têtes sémantiques et zone de défilement focusable.

Validation après cet ajustement : 100 tests PostgreSQL passent, dont un nouveau
contrôle de l’accueil unifié, du tableau et de la zone de compte. Contrôle visuel
sur écran large et étroit ; défilement horizontal limité au tableau.

## Suite : lot 4A

Le lancement simulé, les répétitions et les états incertains sont décrits dans
[le lot 4A](EMPLOYER_SEARCH_LAUNCH.md). Cette extension reste sur une branche
dédiée ; la recette du lot 3 sur 9020 est conservée.
