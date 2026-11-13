# Interface public

Accueil et pages publiques, manifeste PWA, service worker et redirections des anciennes adresses.

[Retour à la couche web](../) · [Architecture](../../../docs/ARCHITECTURE_WEB.md)

## Fichiers

- [__init__.py](__init__.py) — Déclare le paquet Python, sans modèle ni effet au chargement.
- [redirects.py](redirects.py) — Redirige les anciennes adresses déjà livrées vers leurs adresses canoniques.
- [legacy_urls.py](legacy_urls.py) — Isole les adresses retirées, conservées temporairement pour les anciens liens et clients, sans nouveau lien émis vers elles.
- [views.py](views.py) — Traite les requêtes de ce parcours et prépare les réponses.
