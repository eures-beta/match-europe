# Domaine employeur

Offres, établissements, propriété et lecture des sources. Les pages et endpoints sont dans [www/employer/](../www/employer/).

[Paquet applicatif](../) · [Architecture web](../../docs/ARCHITECTURE_WEB.md)

## Dossiers

- [management/](management/) — Commandes du domaine, indépendantes des pages web.
- [migrations/](migrations/) — Historique Django du schéma, conservé lors du déplacement des interfaces.

## Fichiers

- [__init__.py](__init__.py) — Déclare le paquet métier.
- [admin.py](admin.py) — Enregistre les modèles dans l’administration en consultation.
- [apps.py](apps.py) — Configure l’application Django et son identité stable.
- [contact.py](contact.py) — Fournit les coordonnées et liens de contact du conseiller.
- [employer_ownership.py](employer_ownership.py) — Applique les règles de propriété et d’appartenance aux établissements.
- [eures_import.py](eures_import.py) — Règles et fonctions propres au domaine, réutilisables par ses interfaces.
- [models.py](models.py) — Définit les données persistantes, leurs relations et contraintes.
- [occupation_selection.py](occupation_selection.py) — Valide les références métiers sélectionnées pour une offre.
- [offer_ingestion.py](offer_ingestion.py) — Lit les sources d’offres avec des limites de taille et de réseau.
- [offer_requirements.py](offer_requirements.py) — Valide les conditions et critères structurés d’une offre.
- [offer_structuring.py](offer_structuring.py) — Structure les offres avec Albert puis valide le résultat.
- [offer_validation.py](offer_validation.py) — Valide les données communes aux imports, aux écrans et aux commandes.
- [response_practice.py](response_practice.py) — Définit les choix métier des habitudes de réponse employeur.
- [test_data.py](test_data.py) — Prépare les offres fictives des environnements explicitement autorisés.
