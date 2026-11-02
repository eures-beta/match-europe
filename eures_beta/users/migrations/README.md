# Migrations des utilisateurs

Ces migrations créent le compte commun et protègent son rôle en base. La transition depuis auth.User est préparée par la commande migrate avant de résoudre le nouveau graphe.

Voir [la documentation de transition](../../../docs/USER_MODEL.md).

## Contenu de ce dossier

- [0001_initial.py](0001_initial.py) — Prépare et crée le compte unique après contrôle de l’ancienne table utilisateur.
- [0002_kind_immutable.py](0002_kind_immutable.py) — Interdit le changement de kind par un déclencheur PostgreSQL.
- [README.md](README.md) — Présente ce dossier et son contenu.
- [__init__.py](__init__.py) — Identifie le paquet Python.

[Remonter au dossier parent](../).
