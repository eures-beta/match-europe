# Tests des comptes

Ces tests vérifient authentification, unicité des e-mails et contraintes du rôle, y compris les mises à jour directes en base.

Voir [la documentation de transition](../../../docs/USER_MODEL.md).

## Contenu

- [test_test_accounts.py](test_test_accounts.py) — Peuplement idempotent, rôles, langues, CSRF et refus hors environnement fictif ; `make test-accounts-test`.

- [test_admin_model_counts.py](test_admin_model_counts.py) — Vérifie les nombres à la demande, les droits et l’absence de comptage par défaut.

- [test_admin_filters.py](test_admin_filters.py) — Vérifie le bouton traduit, les filtres actifs et les listes sans filtres.
- [admin_filters.test.cjs](admin_filters.test.cjs) — Vérifie le masquage, la restauration et le fonctionnement sans stockage navigateur ; exécuté par `make check-js`.

- [test_email_backend.py](test_email_backend.py) — Vérifie le blocage SMTP local et en recette, et l’autorisation explicite en production sans envoi réel.

- [__init__.py](__init__.py) — Identifie le paquet Python.
- [test_closed_registration.py](test_closed_registration.py) — Vérifie le refus de création de comptes depuis les formulaires et liens publics.
- [test_users.py](test_users.py) — Vérifie les règles des comptes et l’authentification Django.
- [test_account.py](test_account.py) — Vérifie la confidentialité du compte, les langues et la navigation selon le statut staff.
- [test_dashboard.py](test_dashboard.py) — Vérifie l’accès privé et la redirection après connexion pour chaque rôle.
- [test_magic_login.py](test_magic_login.py) — Vérifie les liens à usage unique, les limites, la CSRF, les langues et les sessions.
- [README.md](README.md) — Présente ce dossier et son contenu.

[Remonter au dossier parent](../).
- [admin_navigation.test.cjs](admin_navigation.test.cjs) — Vérifie la navigation masquée par défaut et la conservation des préférences explicites.
