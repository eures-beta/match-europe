# Parcours du prototype

Ce paquet contient le parcours employeur dans `employers`, l’accueil candidat
dans `candidates`, la lecture de documents dans `documents` et le catalogue
métiers partagé dans `occupations`.

Les migrations actuelles sont autonomes dans `employers/migrations/`.
Le dossier `migration_history` et les anciens paquets de compatibilité ont été
supprimés après leur étape de transition. Voir [l'ordre des deux déploiements](../docs/AUTONOMOUS_MIGRATIONS.md).
Les réglages, dépendances et commandes sont centralisés à la racine.
Voir le [README principal](../README.md) pour l’installation et les tests.

La page publique Projet utilise `templates/project.html`, le système gettext
commun et les tests de contenu trilingue dans `tests/common/test_project.py`.

Le journal public utilise `journal.py`, `templates/journal.html` et ses tests
trilingues dans `tests/common/test_journal.py`. Vérifier son contenu avec `make test TEST_ARGS='-k journal -k public_navigation -k project'`.

Les comptes conseiller et employeur partagent désormais [users/](users/), avec
un seul modèle Django `User` et un champ `kind`. Voir [la transition et ses
limites](../docs/USER_MODEL.md).

Le paquet [observability/](observability/) mesure les requêtes et étapes coûteuses
sans conserver leur contenu. Voir [les champs, réglages et limites](../docs/OBSERVABILITY.md).
- [Ressources de l’administration](static/admin/) — Bouton de masquage des filtres et préférence locale du navigateur.


## Séparation métiers et compétences — 9 novembre 2026

Les métiers et recherches restent dans occupations ; catalogues de compétences,
suggestions et composant intégré vivent dans [skills](skills/). Le matching est créé séparément par la PR #160. Le transfert du modèle conserve
la table PostgreSQL, les identifiants, les suggestions et les permissions.


## Interfaces et domaines

[www/](www/) regroupe les vues, formulaires et routes par parcours ; les applications
métier conservent modèles, migrations et services. Voir
[le guide](../docs/ARCHITECTURE_WEB.md). Les dossiers templates, static, locale
et les tests à la racine restent partagés.
