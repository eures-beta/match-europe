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

`make test TESTS=eures_beta.users.tests` couvre les tests du domaine utilisateurs, dont cette page.
`make test` vérifie aussi la cohérence avec les autres parcours. Vérifier la
fiche et les liens en FR/EN/DE avec un compte employeur, un conseiller ordinaire
et un conseiller staff. Aucun changement de schéma ni de droit métier.

## Tableau de bord

`/accounts/dashboard/` est le point d’arrivée commun après une connexion par
lien magique, pour les employeurs, conseillers et comptes staff. La page affiche
« Votre tableau de bord est en construction. » pour les employeurs. Pour les
conseillers habilités, elle liste les comptes employeurs et les invitations en
attente ; voir [les invitations](INVITATIONS.md).
Elle exige une session active, refuse les écritures et n’est pas mise en cache.

Un utilisateur déjà connecté qui ouvre la page de connexion retourne au tableau
de bord. Les paramètres `next` ne changent pas la destination après consommation
du lien magique. Les anciens essais employeur locaux restent séparés.
# Tableau employeur : offres en lecture seule

Le tableau connecté affiche les offres des établissements dont l’employeur est
membre actif et ses brouillons privés explicitement rattachés à son compte.
Les brouillons anonymes du navigateur sont exclus. Le contact d’une offre et
les paramètres d’URL ne donnent aucun droit supplémentaire ; une adhésion
révoquée retire immédiatement les offres de l’établissement.

La liste présente intitulé, établissement, lieu et dernière modification,
25 offres par page, les plus récemment modifiées en premier. Aucun bouton de
création, modification, duplication ou lancement de recherche n’est ajouté.
Ce changement concerne uniquement le tableau ; les autres parcours employeur
conservent leurs propres règles d’accès. Le tableau conseiller est inchangé.

Aucun nouveau modèle, migration ou stockage métier. La route reste privée,
GET uniquement et sans cache ; les sessions existantes restent inchangées.
Le texte des offres est échappé, jamais interprété comme HTML.
Tests : `make test` (dont `employers/tests/test_dashboard.py`).
## Importer une offre depuis le tableau employeur

Le tableau employeur propose le bouton « Importer mon offre d’emploi », identique
à celui de la page publique employeur grâce au fragment commun
`includes/employer_import_button.html`. Il reste visible avec ou sans offre et
ouvre le parcours existant dans la langue courante. Les contrôles d’accès du
parcours d’import restent inchangés. Le tableau conseiller n’est pas modifié.
Le texte qui annonçait la création indisponible est remplacé en FR/EN/DE.
