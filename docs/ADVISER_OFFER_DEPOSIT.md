# Déposer une offre pour un employeur

Un conseiller actif ouvre « Mes offres déposées » et indique l’adresse e-mail
employeur, puis utilise le même import PDF/URL/texte et la même relecture que
l’employeur. Aucun établissement ni adhésion n’est créé, sélectionné ou utilisé.
Le nom de l’entreprise reste une information textuelle de l’offre.

## Compte propriétaire et confirmation

Au premier enregistrement valide, le compte employeur correspondant est réutilisé
sans distinction de casse ou créé actif, sans mot de passe utilisable ni privilège
administrateur. « Actif » signifie autorisé à se connecter, pas déjà connecté ou
adresse déjà vérifiée. Un compte d’un autre rôle ou désactivé bloque le dépôt ;
il n’est jamais converti ni réactivé. Compte et offre sont enregistrés atomiquement.

`JobOffer.created_by` désigne uniquement le compte employeur propriétaire ;
`JobOffer.adviser`, déjà existant, conserve le conseiller déposant. Aucun champ
`employer_contact` supplémentaire. L’adresse employeur n’est stockée que dans
`User.email`, ni dans une colonne de l’offre ni dans son JSON `contact`.
Le nom, le téléphone et la fonction du contact restent propres à l’offre.
Les contrôles de rôle et l’interdiction du doublon JSON existent aussi en PostgreSQL.

La confirmation téléphonique conserve sa date, l’instant de consignation et la
révision confirmée. Le matching est programmé après commit, sans attendre une
connexion de l’employeur. Une nouvelle révision impose une nouvelle confirmation.
Le conseiller peut modifier ses dépôts ; les autres conseillers conservent leur
consultation globale. Les comptes employeurs sont indépendants.

## Connexion de l’employeur

Après commit, un email utilise le lien magique django-sesame et l’écran de
confirmation existants. Aucun nouveau protocole d’activation ni modèle Invitation
n’est nécessaire pour ce compte déjà créé. Le transport commun et son autorisation
d’envoi s’appliquent ; une erreur SMTP ne supprime pas l’offre enregistrée.

L’employeur peut ignorer cet email puis utiliser le formulaire de connexion
habituel plus tard : le nouveau lien donne accès à la même offre via son compte.
Aucun email de contact ne sert à déduire les droits d’une offre d’un autre compte.

## Migration et tests

Les migrations publiées restent immuables. `invitations.0005` retire le lien
établissement introduit par `0004` ; `employers.0010` retire les champs transitoires,
transfère les propriétaires historiques vérifiables et supprime les copies d’email.
Les ambiguïtés de rôle ou d’adresse arrêtent la migration sans écraser les données.
Le retour arrière restaure les champs email à partir du compte propriétaire.
Le retrait des anciennes colonnes est incompatible avec les anciens workers :
coordonner la bascule lors de la livraison. Company et CompanyMembership existants
restent à supprimer dans la PR dédiée, sans dépendance de ce nouveau parcours.

Session de préparation bornée à une heure, liée au conseiller et à un UUID de
dépôt ; anciens onglets, versions périmées, CSRF et refus d’accès sont contrôlés.
`make test TESTS='tests.employers.test_adviser_deposit tests.employers.test_deposit_migrations'`
vérifie le dépôt, les comptes, le lien de connexion, l’isolation et les migrations
non vides. Les services externes sont simulés ; aucun test n’envoie d’email réel.
