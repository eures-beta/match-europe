# Tests des comptes

Ces tests vérifient authentification, unicité des e-mails et contraintes du rôle, y compris les mises à jour directes en base.

Voir [la documentation de transition](../../../docs/USER_MODEL.md).

## Contenu

- [__init__.py](__init__.py) — Identifie le paquet Python.
- [test_closed_registration.py](test_closed_registration.py) — Vérifie le refus de création de comptes depuis les formulaires et liens publics.
- [test_users.py](test_users.py) — Vérifie les règles des comptes et l’authentification Django.
- [test_account.py](test_account.py) — Vérifie la confidentialité du compte, les langues et la navigation selon le statut staff.
- [test_dashboard.py](test_dashboard.py) — Vérifie l’accès privé et la redirection après connexion pour chaque rôle.
- [test_magic_login.py](test_magic_login.py) — Vérifie les liens à usage unique, les limites, la CSRF, les langues et les sessions.
- [README.md](README.md) — Présente ce dossier et son contenu.

[Remonter au dossier parent](../).
