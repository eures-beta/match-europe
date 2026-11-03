# Droits administratifs versionnés

`is_staff` autorise l'entrée dans l'administration après authentification. Il ne
donne aucun droit sur les modèles. Les superutilisateurs constituent l'exception
native de Django et contournent les vérifications de permissions.

La politique de `eures_beta/users/permissions.py` donne au groupe `account-admin`
uniquement `users.view_user`. Ses membres sont les conseillers
actifs avec `is_staff=True`. Les identités et les indicateurs individuels restent
des données en base ; aucune liste nominative n'est versionnée.

Ces administrateurs peuvent consulter les conseillers. Les superadministrateurs
peuvent consulter tous les comptes et les autres modèles. Toute l'administration
est désormais en lecture seule : aucune création, modification, suppression ou
action groupée, même pour un superutilisateur. Cela remplace le formulaire de
création de conseillers introduit précédemment. Le parcours d'invitation employeur
hors administration reste inchangé. Voir [le périmètre de consultation](ADMIN_READONLY.md).

## Réconciliation

Chaque commande complète `migrate` réussie synchronise les droits après création
des permissions Django. Le déploiement existant exécutant cette commande, il
réapplique donc la politique à chaque démarrage de déploiement. Les commandes
`--plan`, `--check` et les migrations ciblées ne la déclenchent pas.

La synchronisation remplace exactement les droits et membres du groupe géré.
Elle enlève aussi les droits directs et les droits d'autres groupes portant sur
le modèle `users.User`, pour empêcher les attributions administratives hors
politique. Ce périmètre inclut désormais `EmployerInvitation` : le groupe
`employer-inviters` autorise les conseillers actifs à consulter les comptes
employeurs et créer des invitations, sans administration. Les droits sur les
autres modèles et leurs groupes sont conservés.
Elle ne modifie aucun indicateur `is_staff`, `is_superuser` ou rôle métier.

Pour réappliquer explicitement la politique à la base du `.env` :

```bash
make permissions-sync
```

Pour tester les droits et leur réconciliation sur PostgreSQL local :

```bash
make permissions-test
```

Cette approche reprend la matrice de groupes et permissions et la réconciliation
de [Les Emplois](https://github.com/gip-inclusion/les-emplois/blob/main/itou/users/management/commands/sync_group_and_perms.py).
La politique de membres et la révocation des droits hors matrice sont propres à
Match Europe. Aucune migration de schéma n'est nécessaire.

L'authentification par lien magique et les invitations sont des travaux séparés.
Créer un conseiller n'envoie actuellement aucun courriel et ne lui donne aucun
mot de passe. La fermeture de l'inscription publique est également indépendante.
