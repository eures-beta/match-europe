# Création de comptes contrôlée

La connexion publique par lien magique ne crée jamais de compte. Elle accepte
uniquement un utilisateur existant et actif, sans permettre de choisir son rôle.
Les rôles sont exclusifs et ne sont jamais convertis automatiquement.

## Parcours autorisés

- Conseiller ou employeur invité : acceptation explicite de l’invitation sécurisée.
- Dépôt d’offre par un conseiller actif : création explicite et atomique d’un
  compte employeur actif si l’adresse n’existe pas, puis rattachement de l’offre.
  Un autre rôle ou un compte désactivé bloque le dépôt. Voir
  [le dépôt conseiller](ADVISER_OFFER_DEPOSIT.md).
- Candidat : parcours dédié avec vérification de l’adresse et confirmation POST
  avant création du compte/profil ; ce n’est pas une inscription employeur ouverte.
- Commandes de gestion et migrations : opérations internes explicites.

Le compte employeur précréé peut se connecter par le même lien magique que tout
compte existant ; aucune activation supplémentaire n’est nécessaire. Actif signifie
non désactivé, pas déjà authentifié. La preuve de possession de l’adresse reste le
lien sécurisé et sa confirmation POST. Les comptes ne sont pas connectés par le
simple dépôt d’une adresse email dans un formulaire.

## Refus maintenus

Les routes génériques signup/register sont absentes. Un visiteur ou candidat ne
peut utiliser le dépôt conseiller. L’import employeur exige son compte existant ;
un import anonyme ne crée pas d’utilisateur. Le formulaire de connexion conserve
sa réponse générique et ne révèle pas l’existence d’un compte.
L’administration Django est en consultation, même pour les superutilisateurs.

## Vérifier

`make test TESTS='tests.users.test_closed_registration tests.employers.test_adviser_deposit'`
contrôle l’absence d’inscription publique et l’exception explicite du dépôt par
un conseiller, avec refus des mauvais rôles et des comptes désactivés.
Les tests utilisent des services simulés et n’envoient aucun email réel.
