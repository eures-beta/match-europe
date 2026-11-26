# Interface matching

Pages de rapprochement, confirmations par offre et conversations partagées.

[Retour à la couche web](../) · [Architecture](../../../docs/ARCHITECTURE_WEB.md)

## Fichiers

- [__init__.py](__init__.py) — Déclare le paquet Python, sans modèle ni effet au chargement.
- [offer_reviews.py](offer_reviews.py) — Présente les conditions d’une offre et recueille les réponses du candidat.
- [conversations.py](conversations.py) — Présente les conversations partagées et contrôle leurs accès.
- [dialogue.py](dialogue.py) — Présente le dialogue de clarification candidat avec validation humaine.
- [urls.py](urls.py) — Associe les URL existantes aux vues, sans changer leur nom public.
- [views.py](views.py) — Traite les requêtes de ce parcours et prépare les réponses.

`/matching/<id>/` et `/matching/<id>/review/` conservent leurs deux vues distinctes : détail général et décision conseiller.

Le suivi conseiller est `/matching/offer-reviews/<id>/` ; la préparation de
conversation est `/matching/offer-reviews/<id>/conversation/` et son fil partagé
est `/matching/conversations/<id>/`. Les identifiants des deux premières routes
sont ceux de la confirmation par offre ; le dernier est celui de la conversation.

Le suivi candidat et les décisions conseiller suivent le [contrat de clôture](../../../docs/REVIEW_HANDOFF.md) ; `offer_reviews.py` expose les remises, compléments et choix de révision du profil.

Le [consentement employeur](employer_consent.py) se prépare depuis le suivi
conseiller. L'employeur retrouve la demande nominative dans son tableau de bord.
Les réponses sur le contact antérieur et les conditions sont enregistrées avant
la décision de mise en relation. La demande est rattachée à une autorisation
candidat précise et son accès cesse si celle-ci est retirée ou devient périmée.
