# Noms des pages et de l’API

`preview` désigne uniquement une recette jetable liée à une PR.
Les pages employeur sont sous `/employer/pages/`, leurs ressources sous `/static/employer/`.
Les API des imports et du diagnostic Push utilisent `/api/` (anciennement `/local-api/`).
Les clients et tests du dépôt sont adaptés ; les anciens endpoints ne sont pas conservés.

Le client JavaScript `window.offerImportAPI`, dans `offer-import-api.js`, est
réservé aux imports d’offres (`/api/imports/`). Il n’est pas un client générique
pour tous les parcours employeurs ni pour le diagnostic Push.

En développement, l’accès explicite sur loopback utilise `ME_EMPLOYER_DEV_ACCESS=1`
(anciennement `ME_EMPLOYER_LOCAL_API`). Ce changement de nom ne modifie ni les
permissions, ni les protections CSRF, ni les restrictions HTTPS de la démo partagée.
Les secrets et réglages propres à chaque environnement restent hors de ce dépôt.
