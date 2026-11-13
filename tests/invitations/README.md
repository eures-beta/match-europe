# Tests des invitations

Vérifient les invitations des trois rôles, le tableau de bord conseiller, les liens signés et les migrations sans perte de données.

- [test_invitations.py](test_invitations.py) — Création, acceptation, droits, expiration et envoi.
- [test_adviser_invitations.py](test_adviser_invitations.py) — Préparation, aperçu, suivi et relances depuis le tableau de bord.
- [test_invitation_names_migration.py](test_invitation_names_migration.py) — Renommage historique et préservation des invitations.
- [test_app_migration.py](test_app_migration.py) — Transfert réversible entre applications sur une base non vide.
- [__init__.py](__init__.py) — Identifie le paquet de tests.

Voir [l’application](../../eures_beta/invitations/) et [les autres tests](../).
