# Routes et API employeur

Les routes canoniques sont indépendantes des noms de templates et des langues :

| Route | Fonction |
| --- | --- |
| `/employer/` | Accueil public employeur |
| `/employer/import/` | Import et relecture, réservés à un employeur connecté |
| `/employer/privacy/` | Notice employeur existante ; contenu distinct de `/privacy/` |
| `/employer/offers/` | Offres et rattachement des brouillons du compte |
| `/employer/offers/<uuid>/` | Fiche d'une offre accessible au compte |
| `/api/job-offers/` | GET liste les offres ; POST enregistre une offre |
| `/api/job-offers/source/` | POST extrait une source, avec accord explicite |
| `/api/job-offers/<uuid>/` | GET lit une offre ; POST met à jour l'offre |

Les actions existantes de modification, duplication et rattachement restent sous
`/employer/`. Le client JavaScript `window.offerImportAPI` reste consacré à
l'import d'offres, pas aux autres API de l'application. Les ressources statiques
restent dans `/static/employer/`.

## Langues et accès

Chaque page rend un seul template gettext pour FR/EN/DE. `?lang=fr|en|de`
permet un lien explicite ; sans paramètre, la sélection commune de langue
s'applique. Les menus et boutons utilisent les routes nommées Django.
Les pages n'acceptent que GET/HEAD ; les écritures passent par leurs actions
protégées. Rôle employeur, propriété des offres, CSRF et contrôle des révisions
restent inchangés. Le retour après connexion accepte seulement l'import local
et une langue valide ; aucune URL externe n'est autorisée.

La notice employeur historique conserve son contenu dans cette PR : son
renommage n'en constitue pas une nouvelle validation éditoriale ou juridique.
Les deux interfaces de matching, les invitations et le Push candidat ne sont
ni renommés ni modifiés par ce nettoyage.

## Vestiges temporaires à supprimer à terme

Tous sont isolés dans [les routes de compatibilité](../eures_beta/www/public/legacy_urls.py).
Aucun lien ou appel applicatif nouveau ne doit les utiliser.

| Ancienne adresse | Compatibilité temporaire |
| --- | --- |
| `/employer/connected/` | 301 vers `/employer/offers/`, paramètres conservés |
| `/employer/pages/{fr,en,de}.html` | 301 vers `/employer/?lang=…` |
| `/employer/pages/import-{fr,en,de}.html` | 301 vers `/employer/import/?lang=…` |
| Anciennes variantes `import-v2-` | Même destination, sans deuxième parcours |
| Anciennes pages `privacy-` | 301 vers `/employer/privacy/?lang=…` |
| `/previews/employer-landing/…` | Mêmes redirections, pour les seuls noms reconnus |
| `/api/imports/…` | 308 vers `/api/job-offers/…`, méthode et corps conservés |

Les anciens retours de connexion déjà enregistrés sont normalisés vers l'import
canonique, sans élargir la liste des destinations autorisées.
Les adresses `/forms/eures-beta/…` antérieures restent aussi des redirections
historiques, sans nouvelle page servie.

La compatibilité des pages est limitée aux anciennes pages connues : aucun
fragment, chemin arbitraire ou fichier source n'est servi. Les anciennes API
utilisent 308, et non 301/302 qui pourraient transformer un POST en GET. Elles
restent soumises à CSRF, puis aux mêmes protections sur la destination.
Ces alias sont des candidats au retrait, pas des routes recommandées. Leur
suppression fera l'objet d'un changement explicite après vérification des
clients encore utilisés ; aucune date de retrait n'est fixée ici.

## Vérifier

```bash
make test TESTS=tests.employers.test_routes
make test TESTS=tests.employers.test_import_access
make test
make test-js
make e2e-test
```

Les tests couvrent langues, accès, retours de connexion, anciens favoris, refus
des fichiers arbitraires et compatibilité des requêtes API.
