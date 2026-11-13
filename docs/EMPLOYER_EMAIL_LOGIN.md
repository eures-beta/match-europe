# Connexion employeur

La connexion employeur utilise le [parcours commun par lien magique](MAGIC_LOGIN.md).
L'ancien formulaire indépendant, sa boîte de réception simulée et ses URL de
confirmation sont retirés. Les anciens liens ne permettent plus de se connecter.

L'espace employeur exige un compte actif de rôle employeur. Les brouillons et
les établissements restent accessibles selon leur propriétaire et les appartenances
actives ; aucune appartenance n'est déduite d'une adresse email.

Le modèle historique `EmployerEmailLink` et sa table sont retirés par la
migration `employers.0007`, uniquement si cette table et les deux tables du
simulateur sont vides. Le système commun de liens magiques reste inchangé.
Les tests de connexion commune couvrent usage unique, expiration et CSRF ;
`make test TESTS=config.test_retired_paths` vérifie que les anciens accès restent introuvables.
