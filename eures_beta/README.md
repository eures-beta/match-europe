# Parcours du prototype

Ce paquet contient le parcours employeur dans `employers`, l’accueil candidat
dans `candidates`, la lecture de documents dans `documents` et le catalogue
métiers partagé dans `occupations`.

`migration_history` conserve les migrations historiques, sans modèle métier.
Les anciens paquets `accounts`, `offers`, `matching`, `conversations` et
`notifications` sont rangés dans son sous-dossier `retired/` ; ils ne sont plus
des applications fonctionnelles.
Voir [pourquoi cet historique reste nécessaire](migration_history/README.md).
Les réglages, dépendances et commandes sont centralisés à la racine.
Voir le [README principal](../README.md) pour l’installation et les tests.

La page publique Projet utilise `templates/project.html`, le système gettext
commun et les tests de contenu trilingue dans `test_project.py`.

Le journal public utilise `journal.py`, `templates/journal.html` et ses tests
trilingues dans `test_journal.py`. Vérifier son contenu avec `make journal-test`.
