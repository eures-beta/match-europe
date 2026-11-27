# Interface adviser

Écrans du conseiller : suivi des rapprochements et historique ; les invitations ont leur propre paquet web.

[Retour à la couche web](../) · [Architecture](../../../docs/ARCHITECTURE_WEB.md)

## Fichiers

- [__init__.py](__init__.py) — Déclare le paquet Python, sans modèle ni effet au chargement.
- [action_queue.py](action_queue.py) — Présente les trois actions et enregistre les recherches externes partagées.
- [history.py](history.py) — Présente l’historique accessible au conseiller.
- [matching.py](matching.py) — Présente la file de rapprochements et les décisions du conseiller.
- [offers.py](offers.py) — Portefeuille, import partagé et modification des offres déposées pour un employeur.
- [offer_forms.py](offer_forms.py) — Email du compte employeur et confirmation téléphonique.

- [record_details.py](record_details.py) — Organise les fiches offre et candidat en résumé et sections lisibles.


- [lifecycle.py](lifecycle.py) — Tableau et ligne de vie par matching, dates, relances et confirmation d’embauche.

- [Planning staff](../../planning/) — Application autonome accessible à tout compte staff actif ; seul le lien de navigation reste intégré à cet espace.
