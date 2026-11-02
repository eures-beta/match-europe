# Parcours du prototype

Ce paquet contient les applications `accounts`, `employers`, `matching`,
`conversations`, `notifications`, `documents`, `candidates` et `offers`.
`migration_history` conserve uniquement les migrations historiques, sans modèle métier.
Voir [l’organisation métier et les dépendances restantes](../docs/VUE_ENSEMBLE.md#organisation-du-code--extraction-des-conversations).
Les réglages, dépendances et commandes sont centralisés à la racine.
Voir le [README principal](../README.md) pour l’installation, le mode démo et les tests.

La page publique Projet utilise `templates/project.html`, le système gettext
commun et les tests de contenu trilingue dans `test_project.py`.

Le journal public utilise `journal.py`, `templates/journal.html` et ses tests
trilingues dans `test_journal.py`. Vérifier son contenu avec `make journal-test`.
