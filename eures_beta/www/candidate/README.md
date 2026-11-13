# Interface candidate

Accueil, questionnaire, confirmation, profil et installation PWA du candidat.

[Retour à la couche web](../) · [Architecture](../../../docs/ARCHITECTURE_WEB.md)

## Fichiers

- [__init__.py](__init__.py) — Déclare le paquet Python, sans modèle ni effet au chargement.
- [journey.py](journey.py) — Orchestre les étapes du questionnaire avec les règles de validation du domaine candidat.
- [landing.py](landing.py) — Présente l’accueil candidat et l’aide à l’installation PWA.
- [push.py](push.py) — Valide la requête HTTP d’abonnement Push de recette, sans déplacer le service d’envoi.
- [registration.py](registration.py) — Présente la confirmation d’adresse et les pages du profil candidat.
- [urls.py](urls.py) — Associe les URL existantes aux vues, sans changer leur nom public.
