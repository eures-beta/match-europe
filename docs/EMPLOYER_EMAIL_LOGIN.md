# Connexion employeur

La connexion employeur utilise le [parcours commun par lien magique](MAGIC_LOGIN.md).
L'ancien formulaire indépendant, sa boîte de réception simulée et ses URL de
confirmation sont retirés. Les anciens liens ne permettent plus de se connecter.

L'espace employeur exige un compte actif de rôle employeur. Les brouillons et
les établissements restent accessibles selon leur propriétaire et les appartenances
actives ; aucune appartenance n'est déduite d'une adresse email.

Les tables historiques des liens sont conservées sans nouvelle écriture ni purge.
Les tests de connexion commune couvrent usage unique, expiration et CSRF ;
`make test-retired-paths` vérifie que les anciens accès restent introuvables.
