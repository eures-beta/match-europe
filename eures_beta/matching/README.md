# Domaine matching

Rapprochement explicable entre candidats et offres : calcul, évaluations et présélection humaine. Ce domaine ne dépend ni des mises en relation ni de leur suivi.

[Paquet applicatif](../) · [Découpage des domaines](../../docs/MATCHING_DOMAINS.md)

## Dossiers

- [management/](management/) — Commandes Django du domaine, indépendantes des pages web.
- [migrations/](migrations/) — Historique versionné du schéma ; les migrations déplacent les tables en conservant les données.
- [static/](static/) — Ressources CSS du navigateur.
- [templates/](templates/) — Templates Django de présentation de ce domaine.

## Fichiers

- [__init__.py](__init__.py) — Déclare le paquet Python.
- [access.py](access.py) — Contrôle l’éligibilité et les droits communs du rapprochement.
- [admin.py](admin.py) — Expose les métadonnées dans l’administration Django en consultation uniquement.
- [engine.py](engine.py) — Calcule les critères et explications du rapprochement.
- [models.py](models.py) — Définit les modèles persistants de ce domaine et leurs contraintes.
- [presentation.py](presentation.py) — Prépare les libellés lisibles des critères de rapprochement.
- [services.py](services.py) — Orchestre calculs, décisions et recalculs après modification du profil ou de l’offre.
- [validation.py](validation.py) — Valide les données métier du rapprochement.

Le [journal `MatchEvent`](../../docs/MATCH_EVENTS.md) appartient au matching et
rassemble les événements de revue, de suivi et de conclusion sans dépendre de leurs modèles.
