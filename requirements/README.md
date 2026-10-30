# Dépendances Python

`base.txt` décrit les dépendances applicatives ; le fichier `requirements.txt` à la racine s’appuie dessus. `test.txt` ajoute les besoins des tests, `push.txt` ceux du diagnostic Push et `quality.txt` les outils de formatage. Les inclusions `-r` dans ces fichiers indiquent les dépendances entre ensembles. Depuis la racine, utiliser `make install-test` pour les tests et `make install-quality` pour les outils de qualité.

[Remonter au dossier parent](../README.md).
