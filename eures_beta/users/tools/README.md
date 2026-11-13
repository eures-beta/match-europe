# Vérification de la transition

Cet outil teste la mise à niveau dans une base locale temporaire, avec des données fictives et une suppression de la base à la fin.

Voir [la documentation de transition](../../../docs/USER_MODEL.md).

## Contenu

- [__init__.py](__init__.py) — Identifie le paquet Python.
- Le diagnostic de mise à niveau PostgreSQL est dans
  [tests/users/verify_upgrade.py](../../../tests/users/verify_upgrade.py),
  lancé avec `make users-upgrade-test`.
- [README.md](README.md) — Présente ce dossier et son contenu.

[Remonter au dossier parent](../).
