# Domaine introductions

Mise en relation : revue de l’offre par le candidat, partage explicite du profil, réponse de l’employeur et conversation à trois. Ce domaine utilise le rapprochement, sans dépendre du suivi.

[Paquet applicatif](../) · [Découpage des domaines](../../docs/MATCHING_DOMAINS.md)

## Dossiers

- [management/](management/) — Commandes Django du domaine, indépendantes des pages web.
- [migrations/](migrations/) — Historique versionné du schéma ; les migrations déplacent les tables en conservant les données.
- [static/](static/) — Ressources CSS du navigateur.
- [templates/](templates/) — Templates Django de présentation de ce domaine.

## Fichiers

- [__init__.py](__init__.py) — Déclare le paquet Python.
- [admin.py](admin.py) — Expose les métadonnées dans l’administration Django en consultation uniquement.
- [adviser_opinion.py](adviser_opinion.py) — Prépare un avis Albert à relire par le conseiller.
- [apps.py](apps.py) — Déclare l’application et son libellé traduit dans l’administration.
- [dialogue_albert.py](dialogue_albert.py) — Adapte le dialogue candidat au client Albert commun.
- [dialogue_services.py](dialogue_services.py) — Valide les réponses proposées et les modifications explicites du profil.
- [employer_consent.py](employer_consent.py) — Recueille la réponse employeur et vérifie les accords avant la conversation.
- [models.py](models.py) — Définit les modèles persistants de ce domaine et leurs contraintes.
- [offer_review_services.py](offer_review_services.py) — Gère les questions par offre, les réponses et les accords de partage.
- [review_email.py](review_email.py) — Envoie la proposition d’offre via le backend email commun.
- [review_notifications.py](review_notifications.py) — Déclenche les notifications minimales après commit.
- [review_workflow.py](review_workflow.py) — Gère la prise en charge et les décisions de revue du conseiller.

Les événements de revue sont enregistrés dans le [journal commun du matching](../../docs/MATCH_EVENTS.md).
