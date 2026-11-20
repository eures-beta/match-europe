# Interface public

Accueil et pages publiques, manifeste PWA, service worker et redirections des anciennes adresses.

[Retour à la couche web](../) · [Architecture](../../../docs/ARCHITECTURE_WEB.md)

## Fichiers

- [__init__.py](__init__.py) — Déclare le paquet Python, sans modèle ni effet au chargement.
- [redirects.py](redirects.py) — Redirige les anciennes adresses déjà livrées vers leurs adresses canoniques.
- [legacy_urls.py](legacy_urls.py) — Isole les adresses retirées, conservées temporairement pour les anciens liens et clients, sans nouveau lien émis vers elles.
- [views.py](views.py) — Traite les requêtes de ce parcours et prépare les réponses.

Les anciennes routes de relecture, invitations et profil employeur restent uniquement dans `legacy_urls.py`. Leurs redirections 308 préservent méthode, corps et paramètres ; les liens applicatifs utilisent les routes nommées canoniques.

Les anciens liens de confirmation et de conversation sont également redirigés
par `legacy_urls.py`. Le service worker conserve un filtre de compatibilité
strict pour ouvrir les notifications déjà livrées avant le renommage ; aucun
nouvel envoi ne génère ces adresses.

Les groupes de routes vestiges ont un délai de 30 jours, un jalon de retrait et
une échéance, selon [la politique et l’inventaire](../../../docs/LEGACY_ROUTES.md).
Les anciennes listes employeur redirigent directement vers le tableau de bord ;
les actions de rattachement retirées répondent 410 sans mutation.
