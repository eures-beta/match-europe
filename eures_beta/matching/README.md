# Domaine des rapprochements

Calcul explicable, décisions, confirmations et conversations. Les interfaces sont dans [www/matching/](../www/matching/) et [www/adviser/](../www/adviser/).

[Paquet applicatif](../) · [Architecture web](../../docs/ARCHITECTURE_WEB.md)

## Dossiers

- [management/](management/) — Commandes du domaine, indépendantes des pages web.
- [migrations/](migrations/) — Historique Django du schéma, conservé lors du déplacement des interfaces.
- [static/](static/) — Ressources du navigateur conservées à leur emplacement actuel.

Le dialogue candidat utilise `static/matching/candidate-conversation.css` :
palette EURES, bulles sobres et cadre téléphone sur ordinateur seulement.
- [templates/](templates/) — Templates du domaine conservés à leur emplacement actuel.

## Fichiers

- [__init__.py](__init__.py) — Déclare le paquet métier.
- [access.py](access.py) — Contrôle les rôles et objets accessibles pour le matching.
- [admin.py](admin.py) — Enregistre les modèles dans l’administration en consultation.
- [adviser_opinion.py](adviser_opinion.py) — Prépare un avis Albert soumis à validation du conseiller.
- [offer_review_services.py](offer_review_services.py) — Recueille les réponses par offre, les intérêts poste/employeur, les refus et l’accord de partage ; calcule l’avancement candidat sans dépendre de l’email.
- [review_email.py](review_email.py) — Envoie la proposition d’offre avec connexion personnelle, conserve le résultat du transport et contrôle les relances.
- [dialogue_albert.py](dialogue_albert.py) — Porte les consignes de conversation naturelle et adapte les clarifications au client Albert commun.
- [dialogue_services.py](dialogue_services.py) — Valide les propositions du dialogue et leurs modifications de profil.
- [engine.py](engine.py) — Calcule les critères et explications du rapprochement.
- [models.py](models.py) — Définit les données persistantes, dont JobOfferSupport et CandidateSupport, accompagnements partagés à cible unique.
- [presentation.py](presentation.py) — Prépare les libellés et données de présentation des résultats.
- [search_queue.py](search_queue.py) — Distingue recherches externes, calculs absents/périmés et informations insuffisantes.
- [services.py](services.py) — Orchestre calculs et décisions, dont les déclenchements après enregistrement d’une offre ou d’un profil candidat.
- [validation.py](validation.py) — Valide les données métier du rapprochement.
