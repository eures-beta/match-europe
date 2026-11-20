# Routes et API employeur

Les routes canoniques sont indépendantes des noms de templates et des langues :

| Route | Fonction |
| --- | --- |
| `/employer/` | Accueil public employeur |
| `/employer/import/` | Import et relecture, réservés à un employeur connecté |
| `/employer/privacy/` | Notice employeur existante ; contenu distinct de `/privacy/` |
| `/accounts/dashboard/` | Tableau de bord et offres du compte connecté |
| `/employer/offers/<uuid>/` | Fiche d'une offre accessible au compte |
| `/api/job-offers/` | GET liste les offres ; POST enregistre une offre |
| `/api/job-offers/source/` | POST extrait une source, avec accord explicite |
| `/api/job-offers/<uuid>/` | GET lit une offre ; POST met à jour l'offre |

Les actions existantes de modification et duplication restent sous
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

## Vestiges temporaires : 30 jours

Les anciennes adresses sont isolées dans
[legacy_urls.py](../eures_beta/www/public/legacy_urls.py), avec leur jalon de retrait
et leur échéance. Aucun écran ne doit les émettre. La règle, les dates et la liste
complète sont dans [l’inventaire des routes vestiges](LEGACY_ROUTES.md).

Les liens « Retour aux offres » utilisent directement le tableau de bord.
`/employer/offers/` et `/employer/connected/` ne servent plus d’écran : ils
redirigent directement vers `/accounts/dashboard/`, en conservant les paramètres.
Les anciennes actions de rattachement répondent 410 sans exécuter de traitement.

Les anciennes API utilisent 308 pour préserver méthode et corps, avec CSRF et
les mêmes droits sur leur destination. Les anciennes pages connues utilisent
301 pour GET/HEAD et refusent les écritures ; aucun fragment arbitraire n’est servi.
Les anciens retours de connexion sont normalisés vers l’import canonique sans
élargir les destinations autorisées. Ces helpers suivent les mêmes échéances.

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
