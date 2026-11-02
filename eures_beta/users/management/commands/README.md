# Préparation des migrations utilisateurs

La commande migrate étend celle de Django pour préparer la transition depuis l’ancien modèle utilisateur sans fausse migration.

Voir [la documentation de transition](../../../../docs/USER_MODEL.md).

## Contenu

- [sync_group_and_perms.py](sync_group_and_perms.py) — Réapplique la politique administrative versionnée ; `make permissions-sync`. La commande complète `migrate` l'appelle automatiquement après réussite.
- [__init__.py](__init__.py) — Identifie le paquet Python.
- [migrate.py](migrate.py) — Prépare la première migration utilisateur puis appelle la commande Django native.
- [README.md](README.md) — Présente ce dossier et son contenu.

[Remonter au dossier parent](../).
