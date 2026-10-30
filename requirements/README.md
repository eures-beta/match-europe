# Dépendances Python

`base.txt` décrit les dépendances applicatives ; le fichier `requirements.txt` à la racine s’appuie dessus. `test.txt` ajoute les besoins des tests, `push.txt` ceux du diagnostic Push et `quality.txt` les outils de formatage. Les inclusions `-r` dans ces fichiers indiquent les dépendances entre ensembles. Depuis la racine, utiliser `make install-test` pour les tests et `make install-quality` pour les outils de qualité.

## Contenu de ce dossier

### Fichiers

- [base.txt](base.txt) — Liste les dépendances Python nécessaires à l’application.
- [push.txt](push.txt) — Liste les dépendances du diagnostic Push.
- [quality.txt](quality.txt) — Liste les outils de qualité et de formatage Python et HTML.
- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [test.txt](test.txt) — Ajoute les dépendances nécessaires à la suite de tests.

[Remonter au dossier parent](../).
