# Préparation des migrations utilisateurs

La commande migrate étend celle de Django pour préparer la transition depuis l’ancien modèle utilisateur sans fausse migration.

Voir [la documentation de transition](../../../../docs/USER_MODEL.md).

## Contenu

- [seed_test_accounts.py](seed_test_accounts.py) — Prépare les comptes et offres fictifs sans réinitialisation ; `make test-accounts-seed`.

- [Simulation des invitations](../../../invitations/management/commands/invitation_email.py) — Commande possédée par l'application invitations.
- [login_email.py](login_email.py) — Simulation privée d'une connexion pour un compte actif existant, sans envoi.

- [sync_group_and_perms.py](sync_group_and_perms.py) — Réapplique la politique administrative versionnée ; `make permissions-sync`. La commande complète `migrate` l'appelle automatiquement après réussite.
- [__init__.py](__init__.py) — Identifie le paquet Python.
- [migrate.py](migrate.py) — Prépare la première migration utilisateur puis appelle la commande Django native.
- [README.md](README.md) — Présente ce dossier et son contenu.

[Remonter au dossier parent](../).
