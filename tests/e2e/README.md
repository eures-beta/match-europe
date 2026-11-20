# Parcours HTTP et mémoire

Ce banc utilise PostgreSQL et Gunicorn dans des conteneurs isolés pour vérifier
les vrais parcours sous un plafond de 256 Mio, avec services externes capturés.
Voir [les tests](../) et [le guide](../../docs/TESTS.md).

- [run.py](run.py) : prépare les conteneurs et rapporte les mesures de mémoire.
- [Dockerfile](Dockerfile) : construit l'environnement des parcours.
- [bootstrap.py](bootstrap.py) : migre la base fictive, peuple deux fois les comptes
  de démonstration puis lance le serveur avec les options métier normales.
- [settings.py](settings.py) : configure les frontières externes du banc.
- [fixtures.py](fixtures.py) : fournit les données fictives des parcours.
- [journeys.py](journeys.py) : parcourt les écrans HTTPS et vérifie leurs résultats.
- [test_journeys.py](test_journeys.py) : vérifie les helpers du client HTTP.
- [__init__.py](__init__.py) : déclare le paquet de tests.
