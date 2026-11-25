# Tests des invitations

Vérifient les invitations des trois rôles, le tableau de bord conseiller, les liens signés et les migrations sans perte de données.

- [historical.py](historical.py) — Contrat signé figé pour les fixtures des anciens schémas ; la lecture par le service actuel est vérifiée après la migration des rôles.
- [test_invitations.py](test_invitations.py) — Création, acceptation, droits, expiration et envoi ; neuf combinaisons de langues FR/EN/DE entre conseiller et destinataire.
- [test_adviser_invitations.py](test_adviser_invitations.py) — Préparation, aperçu, envois individuels et CSV au-delà de dix, résultats d’échec, protection contre les rejeux et relances à 24 heures.
- [test_invitation_names_migration.py](test_invitation_names_migration.py) — Renommage historique et préservation des invitations.
- [test_app_migration.py](test_app_migration.py) — Transfert réversible entre applications sur une base non vide.
- [__init__.py](__init__.py) — Identifie le paquet de tests.

Voir [l’application](../../eures_beta/invitations/) et [les autres tests](../).
