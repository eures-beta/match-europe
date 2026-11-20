# Routes vestiges : compatibilité pendant 30 jours

Une route devient vestige quand une version déployée cesse de l’émettre et la
remplace par une adresse canonique, ou retire la fonctionnalité correspondante.
Une route encore reliée aux écrans actuels n’est pas du code mort.

## Règle et entretien

- Conserver la compatibilité **30 jours après le premier déploiement du retrait**.
  La création d’une PR, sa fusion et sa livraison sont des événements distincts.
- Regrouper ces routes dans [legacy_urls.py](../eures_beta/www/public/legacy_urls.py).
  Commenter chaque groupe avec sa date ou son jalon de retrait et son échéance.
  Les liens, formulaires, e-mails et nouveaux Push utilisent les noms canoniques.
- Lors de la première livraison, renseigner les dates calendaires du groupe en
  attente. Une retouche, un renommage ou un rebase ne relance jamais les 30 jours.
- À chaque entretien de pile et avant livraison, examiner les échéances. À J+30,
  retirer le groupe dans un commit d’entretien dédié : routes, helpers devenus
  inutiles, anciens retours de connexion et listes de compatibilité du service
  worker, avec leurs tests et cette liste. Une prolongation demande une décision
  explicite, une raison et une nouvelle date ; aucune conservation indéfinie.
- Vérifier qu’aucun écran n’émet encore ces adresses, que les destinations gardent
  leurs contrôles d’accès et que les écritures gardent méthode, corps et CSRF.
  Une action supprimée répond 410 sans exécuter l’ancien traitement.
- La suppression est revue, testée et déployée. Aucun interrupteur d’horloge ne
  change silencieusement les routes en production ; aucun suivi de fond implicite.

## Retraits de la PR #261

Jalon : **premier déploiement de #261**. Date non encore connue à la rédaction ;
retrait des trois compatibilités **30 jours après cette livraison**. Renseigner
ici et dans le commentaire du groupe les dates réelles lors de cette livraison.

| Ancienne route | Réponse de compatibilité |
| --- | --- |
| `/employer/offers/` | 301 vers `/accounts/dashboard/`, GET/HEAD uniquement |
| `/employer/attach/` | 410, ancien rattachement supprimé |
| `/employer/drafts/<uuid:id>/attach/` | 410, ancien rattachement supprimé |

« Retour aux offres » émet directement `/accounts/dashboard/?lang=…` depuis
le détail, l’édition et les écrans de conflit/verrouillage. Aucun nom de route
`employer_offers` ne reste disponible pour générer l’ancienne adresse de liste.
Les routes de détail `/employer/offers/<uuid:id>/` et d’édition/duplication restent
actives et canoniques : elles ne font pas partie des vestiges.

## Routes déjà vestiges lors de l’inventaire du 20 novembre 2026

Leur date exacte de premier déploiement n’est pas reconstituée ici. Cette première
mise en place de la politique fixe une **borne maximale au 20 décembre 2026**,
sans prétendre qu’elles sont devenues vestiges le 20 novembre. Ce délai initial
ne doit pas être reconduit par les prochaines modifications.

| Ancienne route | Destination canonique |
| --- | --- |
| `/matching/candidate/` | `/candidate/offer-reviews/` |
| `/matching/candidate/<int:pk>/` | `/candidate/offer-reviews/<pk>/` |
| `/matching/candidate/<int:pk>/dialogue/` | `/candidate/offer-reviews/<pk>/dialogue/` |
| `/accounts/dashboard/conversations/<int:pk>/` | `/matching/offer-reviews/<pk>/` |
| `/matching/shared/start/<int:pk>/` | `/matching/offer-reviews/<pk>/conversation/` |
| `/matching/shared/<int:pk>/` | `/matching/conversations/<pk>/` |
| `/accounts/dashboard/matching/<int:pk>/` | `/matching/<pk>/review/` |
| `/accounts/dashboard/invitations/` | `/adviser/invitations/` |
| `/accounts/employers/invite/` | `/adviser/invitations/new/` |
| `/api/employer/response-practice/` | `/api/employer/profile/` |
| `/employer/connected/` | `/accounts/dashboard/` directement, sans chaîne de vestiges |
| `/employer/pages/<path:path>` | Accueil, import ou confidentialité employeur selon le nom reconnu |
| `/previews/employer-landing/<path:path>` | Mêmes destinations employeur |
| `/api/imports/` | `/api/job-offers/` |
| `/api/imports/source/` | `/api/job-offers/source/` |
| `/api/imports/<uuid:id>/` | `/api/job-offers/<id>/` |
| `/forms/eures-beta/` | `/` |
| `/forms/eures-beta/candidate` | `/candidate/` |
| `/forms/eures-beta/stat` | `/statistics/` |
| `/forms/eures-beta/le-projet` | `/project/` |
| `/forms/eures-beta/journal` | `/journal/` |

Les dix premières routes redirigent en 308, avec méthode, corps et paramètres
conservés. Les anciennes API `imports` utilisent également 308. Les pages et
l’ancienne entrée employeur utilisent 301 pour GET/HEAD et refusent les écritures.
Les anciens noms de pages reconnus sont `{fr,en,de}.html`,
`import-{fr,en,de}.html`, `import-v2-{fr,en,de}.html` et
`privacy-{fr,en,de}.html`. Aucun autre fragment de template n’est exposé.

Le filtre `legacyNotificationUrl` du service worker accompagne uniquement les
anciennes adresses Push de ce groupe ; il doit disparaître à la même échéance.

## Vérification

```bash
make test TESTS=tests.employers.test_routes
make test TESTS=tests.employers.test_employer_workspace
make test TESTS=tests.common.test_workspace_routes
make test-js
```

Vérifier les redirections en un seul saut, les paramètres de langue/pagination,
les refus de POST et l’absence de contournement de connexion ou de propriété.
