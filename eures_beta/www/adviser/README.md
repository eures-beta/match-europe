# Interface adviser

Écrans du conseiller : suivi des rapprochements et historique ; les invitations ont leur propre paquet web.

[Retour à la couche web](../) · [Architecture](../../../docs/ARCHITECTURE_WEB.md)

## Fichiers

- [__init__.py](__init__.py) — Déclare le paquet Python, sans modèle ni effet au chargement.
- [action_queue.py](action_queue.py) — Présente les trois actions et enregistre les recherches externes partagées.
- [history.py](history.py) — Présente l’historique accessible au conseiller.
- [matching.py](matching.py) — Présente la file de rapprochements et les décisions du conseiller.

- [record_details.py](record_details.py) — Organise les fiches offre et candidat en résumé et sections lisibles.
