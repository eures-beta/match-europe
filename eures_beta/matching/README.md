# Domaine des rapprochements

Calcul explicable, décisions, confirmations et conversations. Les interfaces sont dans [www/matching/](../www/matching/) et [www/adviser/](../www/adviser/).

[Paquet applicatif](../) · [Architecture web](../../docs/ARCHITECTURE_WEB.md)

## Dossiers

- [management/](management/) — Commandes du domaine, indépendantes des pages web.
- [migrations/](migrations/) — Historique Django du schéma, conservé lors du déplacement des interfaces.
- [static/](static/) — Ressources du navigateur conservées à leur emplacement actuel.
- [templates/](templates/) — Templates du domaine conservés à leur emplacement actuel.

## Fichiers

- [__init__.py](__init__.py) — Déclare le paquet métier.
- [access.py](access.py) — Contrôle les rôles et objets accessibles pour le matching.
- [admin.py](admin.py) — Enregistre les modèles dans l’administration en consultation.
- [adviser_opinion.py](adviser_opinion.py) — Prépare un avis Albert soumis à validation du conseiller.
- [confirmation_services.py](confirmation_services.py) — Recueille les réponses par offre et l’accord de partage du profil.
- [dialogue_albert.py](dialogue_albert.py) — Adapte les échanges de clarification au client Albert commun.
- [dialogue_services.py](dialogue_services.py) — Valide les propositions du dialogue et leurs modifications de profil.
- [engine.py](engine.py) — Calcule les critères et explications du rapprochement.
- [models.py](models.py) — Définit les données persistantes, leurs relations et contraintes.
- [presentation.py](presentation.py) — Prépare les libellés et données de présentation des résultats.
- [services.py](services.py) — Orchestre calculs et décisions avec contrôles de version et concurrence.
- [validation.py](validation.py) — Valide les données métier du rapprochement.
