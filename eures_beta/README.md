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
commun et les tests de contenu trilingue dans `test_project.py`.

Le journal public utilise `journal.py`, `templates/journal.html` et ses tests
trilingues dans `test_journal.py`. Vérifier son contenu avec `make journal-test`.

Les comptes conseiller et employeur partagent désormais [users/](users/), avec
un seul modèle Django `User` et un champ `kind`. Voir [la transition et ses
limites](../docs/USER_MODEL.md).

Le paquet [observability/](observability/) mesure les requêtes et étapes coûteuses
sans conserver leur contenu. Voir [les champs, réglages et limites](../docs/OBSERVABILITY.md).
- [Ressources de l’administration](static/admin/) — Bouton de masquage des filtres et préférence locale du navigateur.
