# Interface matching

Pages de rapprochement, confirmations par offre et conversations partagées.

[Retour à la couche web](../) · [Architecture](../../../docs/ARCHITECTURE_WEB.md)

## Fichiers

- [__init__.py](__init__.py) — Déclare le paquet Python, sans modèle ni effet au chargement.
- [confirmations.py](confirmations.py) — Présente les conditions d’une offre et recueille les réponses du candidat.
- [conversations.py](conversations.py) — Présente les conversations partagées et contrôle leurs accès.
- [dialogue.py](dialogue.py) — Présente le dialogue de clarification candidat avec validation humaine.
- [urls.py](urls.py) — Associe les URL existantes aux vues, sans changer leur nom public.
- [views.py](views.py) — Traite les requêtes de ce parcours et prépare les réponses.
