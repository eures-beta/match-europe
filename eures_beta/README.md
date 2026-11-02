# Parcours du prototype

Ce paquet contient le parcours employeur dans `employers`, l’accueil candidat
dans `candidates`, la lecture de documents dans `documents` et le catalogue
métiers partagé dans `occupations`.

Les migrations actuelles sont autonomes dans `employers/migrations/`.
Le dossier `migration_history` et les anciens paquets de compatibilité ont été
supprimés après leur étape de transition. Voir [l'ordre des deux déploiements](../docs/AUTONOMOUS_MIGRATIONS.md).
Les réglages, dépendances et commandes sont centralisés à la racine.
Voir le [README principal](../) pour l’installation et les tests.

La page publique Projet utilise `templates/project.html`, le système gettext
commun et les tests de contenu trilingue dans `test_project.py`.

Le journal public utilise `journal.py`, `templates/journal.html` et ses tests
trilingues dans `test_journal.py`. Vérifier son contenu avec `make journal-test`.

Les comptes conseiller et employeur partagent désormais [users/](users/), avec
un seul modèle Django `User` et un champ `kind`. Voir [la transition et ses
limites](../docs/USER_MODEL.md).
## Contenu de ce dossier

### Dossiers

- [candidates/](candidates/) — Cette application sert le nouvel accueil candidat à trois choix.
- [documents/](documents/) — Ce paquet fournit les lecteurs PDF et l’extraction de champs réutilisés par le parcours employeur.
- [employers/](employers/) — Cette application regroupe les identités et établissements employeurs, les habilitations, les imports d’offres, la connexion par lien et l’espace de travail.
- [locale/](locale/) — Les textes sources sont en anglais dans le code Python et les templates Django.
- [occupations/](occupations/) — Ce paquet fournit la recherche locale dans les références ESCO et ROME.
- [static/](static/) — Ce dossier contient CSS, JavaScript, service worker et ressources visuelles partagées.
- [templates/](templates/) — Django transforme ces templates en pages HTML.

### Fichiers

- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [__init__.py](__init__.py) — Identifie ce dossier comme un paquet Python.
- [choices.py](choices.py) — Centralise les choix partagés entre domaines.
- [demo.py](demo.py) — Regroupe les mécanismes du scénario fictif et ses réglages associés.
- [demo_access.py](demo_access.py) — Centralise les conditions d’accès au prototype partagé.
- [journal.py](journal.py) — Décrit les entrées du journal avec des textes gettext.
- [logging.py](logging.py) — Configure la journalisation de l’application.
- [redirects.py](redirects.py) — Gère les redirections depuis les anciennes adresses.
- [template_layout.py](template_layout.py) — Vérifie la lisibilité et la structure des templates.
- [test_employer_auth_translation.py](test_employer_auth_translation.py) — Tests portant sur traduction de la connexion employeur.
- [test_employer_import_translation.py](test_employer_import_translation.py) — Tests portant sur traduction des pages d’import.
- [test_employer_landing_translation.py](test_employer_landing_translation.py) — Tests portant sur traduction de l’accueil employeur.
- [test_employer_privacy_translation.py](test_employer_privacy_translation.py) — Tests portant sur traduction de la notice de confidentialité.
- [test_entrypoints.py](test_entrypoints.py) — Tests portant sur points d’entrée du site.
- [test_home.py](test_home.py) — Tests portant sur page d’accueil.
- [test_journal.py](test_journal.py) — Vérifie le journal, ses jalons et ses traductions.
- [test_language_navigation.py](test_language_navigation.py) — Tests portant sur navigation et bascule de langue.
- [test_layout.py](test_layout.py) — Tests portant sur cadre HTML des pages.
- [test_logging.py](test_logging.py) — Tests portant sur journalisation applicative.
- [test_project.py](test_project.py) — Vérifie la page Projet et son contenu dans les trois langues.
- [test_public_navigation.py](test_public_navigation.py) — Tests portant sur navigation publique et redirections.
- [test_retired_prototype.py](test_retired_prototype.py) — Vérifie que les anciens parcours retirés ne sont plus exposés.
- [test_shared_brand.py](test_shared_brand.py) — Tests portant sur logo et identité partagés.
- [test_template_layout.py](test_template_layout.py) — Tests portant sur structure et lisibilité des templates.
- [test_translation_catalogs.py](test_translation_catalogs.py) — Tests portant sur catalogues de traduction.
- [testing.py](testing.py) — Fournit des assertions HTML pour les tests.
- [translation_check.py](translation_check.py) — Vérifie les catalogues gettext.
- [views.py](views.py) — Traite les requêtes HTTP et prépare les réponses de ce domaine.

[Remonter au dossier parent](../).
