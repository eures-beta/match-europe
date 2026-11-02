# Comptes utilisateurs

Ce paquet regroupe le compte Django unique des conseillers et employeurs. Le champ `kind` porte le rôle ; les établissements et leurs adhésions restent dans employers.

Voir [la documentation de transition](../../docs/USER_MODEL.md).

## Contenu de ce dossier

### Dossiers

- [management/](management/) — Ce dossier permet à Django de découvrir les commandes du domaine utilisateurs.
- [migrations/](migrations/) — Ces migrations créent le compte commun et protègent son rôle en base. La transition depuis auth.User est préparée par la commande migrate avant de résoudre le nouveau graphe.
- [tests/](tests/) — Ces tests vérifient authentification, unicité des e-mails et contraintes du rôle, y compris les mises à jour directes en base.
- [tools/](tools/) — Cet outil teste la mise à niveau dans une base locale temporaire, avec des données fictives et une suppression de la base à la fin.

### Fichiers

- [README.md](README.md) — Présente ce dossier et son contenu.
- [__init__.py](__init__.py) — Identifie le paquet Python.
- [admin.py](admin.py) — Adapte l’administration Django au compte sans username et au kind immuable.
- [apps.py](apps.py) — Déclare l’application Django users.
- [models.py](models.py) — Définit User et son gestionnaire.

[Remonter au dossier parent](../).
