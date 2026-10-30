# Parcours du prototype

Ce paquet contient les applications `accounts`, `employers`, `matching`,
`conversations`, `notifications`, `documents`, `candidates` et `offers`.
`migration_history` conserve uniquement les migrations historiques, sans modèle métier.
Voir [l’organisation métier et les dépendances restantes](../docs/VUE_ENSEMBLE.md#organisation-du-code--extraction-des-conversations).
Les réglages, dépendances et commandes sont centralisés à la racine.
Voir le [README principal](../) pour l’installation, le mode démo et les tests.

## Contenu de ce dossier

### Dossiers

- [accounts/](accounts/) — Cette application gère les profils liés aux utilisateurs Django, leurs rôles, les jetons d’accès et les événements d’audit.
- [candidates/](candidates/) — Cette application porte le modèle candidat, sa modification et le nouvel accueil candidat.
- [conversations/](conversations/) — Cette application regroupe les conversations et leurs messages, avec les formulaires, vues et permissions associés.
- [documents/](documents/) — Cette application gère les documents, leur téléversement et leur téléchargement.
- [employers/](employers/) — Cette application regroupe les identités et établissements employeurs, les habilitations, les imports d’offres, la connexion par lien et l’espace de travail.
- [locale/](locale/) — Les textes sources sont en anglais dans le code Python et les templates Django.
- [matching/](matching/) — Cette application gère les rapprochements entre offres et candidats, les réponses, leur revue et les accords précédant une conversation.
- [migration_history/](migration_history/) — Ce paquet conserve l’historique de l’ancienne application `journeys`, dont le label technique reste nécessaire aux bases existantes.
- [notifications/](notifications/) — Cette application enregistre les notifications destinées aux utilisateurs et permet de les consulter ou de les marquer comme lues.
- [occupations/](occupations/) — Ce paquet fournit la recherche locale dans les références ESCO et ROME.
- [offers/](offers/) — Cette application porte les offres et leurs questions de préqualification, avec leurs formulaires, services, vues et permissions.
- [static/](static/) — Ce dossier contient CSS, JavaScript, service worker et ressources visuelles partagées.
- [templates/](templates/) — Django transforme ces fichiers en pages HTML en leur fournissant des données.

### Fichiers

- [__init__.py](__init__.py) — Identifie ce dossier comme un paquet Python.
- [choices.py](choices.py) — Centralise les listes de choix partagées entre domaines.
- [demo.py](demo.py) — Regroupe les mécanismes du scénario fictif et ses réglages associés.
- [demo_access.py](demo_access.py) — Centralise les conditions d’accès au scénario fictif partagé.
- [logging.py](logging.py) — Configure les mécanismes de journalisation applicative.
- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [redirects.py](redirects.py) — Gère les redirections de compatibilité depuis les anciennes adresses.
- [template_layout.py](template_layout.py) — Tests portant sur les contraintes de structure et lisibilité des templates.
- [test_demo.py](test_demo.py) — Tests portant sur scénario fictif.
- [test_employer_auth_translation.py](test_employer_auth_translation.py) — Tests portant sur traduction de la connexion employeur.
- [test_employer_import_translation.py](test_employer_import_translation.py) — Tests portant sur traduction des pages d’import.
- [test_employer_landing_translation.py](test_employer_landing_translation.py) — Tests portant sur traduction de l’accueil employeur.
- [test_employer_privacy_translation.py](test_employer_privacy_translation.py) — Tests portant sur traduction de la notice de confidentialité.
- [test_entrypoints.py](test_entrypoints.py) — Tests portant sur points d’entrée du site.
- [test_home.py](test_home.py) — Tests portant sur page d’accueil.
- [test_language_navigation.py](test_language_navigation.py) — Tests portant sur navigation et bascule de langue.
- [test_layout.py](test_layout.py) — Tests portant sur cadre HTML des pages.
- [test_localization.py](test_localization.py) — Tests portant sur localisation des écrans.
- [test_logging.py](test_logging.py) — Tests portant sur journalisation applicative.
- [test_public_navigation.py](test_public_navigation.py) — Tests portant sur navigation publique et redirections.
- [test_shared_brand.py](test_shared_brand.py) — Tests portant sur logo et identité partagés.
- [test_template_layout.py](test_template_layout.py) — Tests portant sur structure et lisibilité des templates.
- [test_translation_catalogs.py](test_translation_catalogs.py) — Tests portant sur catalogues de traduction.
- [testing.py](testing.py) — Fournit des assertions HTML partagées par les tests.
- [testing_support.py](testing_support.py) — Prépare les données fictives et utilitaires communs des tests.
- [translation_check.py](translation_check.py) — Tests portant sur que les catalogues gettext sont complets et sans traductions fuzzy.
- [views.py](views.py) — Traite les requêtes HTTP et prépare les réponses de ce domaine.

[Remonter au dossier parent](../).
