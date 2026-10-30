# Parcours employeur

Cette application regroupe les identités et établissements employeurs, les habilitations, les imports d’offres, la connexion par lien et l’espace de travail. Les modules de lecture d’offres traitent notamment France Travail et EURES. Les imports employeurs restent distincts des offres du parcours de matching. Voir [l’import par URL](../../docs/OFFER_URL_IMPORT.md) et [l’espace employeur](../../docs/EMPLOYER_OFFER_WORKSPACE.md).

## Contenu de ce dossier

### Dossiers

- [migrations/](migrations/) — Ces fichiers décrivent l’évolution du schéma et de l’état Django pour les imports, accès et parcours employeur.
- [tests/](tests/) — Ces tests vérifient les imports, accès et parcours employeur.

### Fichiers

- [__init__.py](__init__.py) — Identifie ce dossier comme un paquet Python.
- [apps.py](apps.py) — Déclare l’application auprès de Django et son identité technique.
- [employer_api.py](employer_api.py) — Implémente les échanges HTTP de l’API d’import d’offres.
- [employer_login.py](employer_login.py) — Gère la connexion employeur par lien et ses contrôles.
- [employer_ownership.py](employer_ownership.py) — Tests portant sur les habilitations des employeurs sur leurs établissements et objets.
- [employer_search.py](employer_search.py) — Gère le lancement et les états de la recherche employeur.
- [employer_workspace.py](employer_workspace.py) — Prépare les opérations de l’espace employeur sur ses offres importées.
- [establishments.py](establishments.py) — Recherche et normalise les informations d’établissement.
- [eures_import.py](eures_import.py) — Lit les offres EURES avec un adaptateur spécifique et ses protections.
- [forms.py](forms.py) — Définit les formulaires et la validation des saisies de ce domaine.
- [models.py](models.py) — Décrit les modèles persistants et leurs relations pour ce domaine.
- [occupation_selection.py](occupation_selection.py) — Valide et reconstruit les choix de métiers issus du catalogue.
- [offer_ingestion.py](offer_ingestion.py) — Orchestre la lecture et la préparation des offres importées.
- [push_strings.py](push_strings.py) — Centralise les textes traduits du diagnostic Push.
- [push_test.py](push_test.py) — Implémente le diagnostic des notifications Push et ses protections.
- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [urls.py](urls.py) — Associe les chemins HTTP aux vues correspondantes.
- [views.py](views.py) — Traite les requêtes HTTP et prépare les réponses de ce domaine.

[Remonter au dossier parent](../).
