# Mon compte et tableau de bord

`/accounts/me/` affiche le rôle, l’e-mail, le nom lorsqu’il est renseigné et la
date de création du compte connecté. La page conserve le layout public et ses
logos. Un même template gettext sert le français, l’anglais et l’allemand.

La page est en lecture seule : aucun formulaire de modification, aucune donnée
d’un autre compte ni information de mot de passe. `login_required` vérifie la
connexion côté serveur et `never_cache` empêche la mise en cache de la fiche.
Une adresse saisie dans la query string ne permet pas de consulter un autre compte.

L’en-tête partagé propose « Tableau de bord », « Mon compte » puis « Me déconnecter » aux comptes
connectés. Les comptes `is_staff=True` ont aussi un lien « Admin » vers
l’administration Django existante ; ses permissions continuent à s’appliquer.
Le bouton de connexion reste visible pour les visiteurs anonymes et la
déconnexion exige toujours un POST protégé par CSRF.

`make login-test` couvre les tests du domaine utilisateurs, dont cette page.
`make test` vérifie aussi la cohérence avec les autres parcours. Vérifier la
fiche et les liens en FR/EN/DE avec un compte employeur, un conseiller ordinaire
et un conseiller staff. Aucun changement de schéma ni de droit métier.

## Tableau de bord

`/accounts/dashboard/` est le point d’arrivée commun après une connexion par
lien magique, pour les employeurs, conseillers et comptes staff. La page affiche
uniquement « Votre tableau de bord est en construction. » dans le layout commun.
Elle ne liste ni offres ni employeurs et ne modifie pas les permissions métier.
Elle exige une session active, refuse les écritures et n’est pas mise en cache.

Un utilisateur déjà connecté qui ouvre la page de connexion retourne au tableau
de bord. Les paramètres `next` ne changent pas la destination après consommation
du lien magique. Les anciens essais employeur locaux restent séparés.
