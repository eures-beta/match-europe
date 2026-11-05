# Protection et conservation des données

## Reprise du cadre existant — 5 novembre 2026

La page publique `/privacy/?lang=fr` (FR/EN/DE) reprend les durées et principes
du code Flask `eures-beta/match-europe-flask`, commit `a95d962`, dans
`forms/eures-beta/app.js` (bloc `privacyPage`). Elle utilise les traductions
Django et la coque publique existante. Les liens candidat, employeur, import
et connexion employeur pointent vers cette page commune.

À la demande d'Eric, la présentation reprend les composants du Flask : carte
de titre et encart latéral, cartes thématiques en colonnes, tableau des durées
et blocs de contact. Sur mobile, les cartes s'empilent et les deux colonnes du
tableau restent lisibles sans largeur minimale imposée. Les informations et
limites du nouveau parcours sont conservées.

La notice employeur antérieure du 3 août reste accessible depuis cette page
pour ne pas supprimer les informations spécifiques déjà travaillées. Son
avertissement historique et son absence de validation pour le parcours actuel
restent visibles ; elle renvoie aussi vers la nouvelle page commune.
Le contact professionnel repris est celui déjà présent dans la coque du projet.

## Durées de référence héritées de Flask

| Catégorie | Durée / événement de départ |
| --- | --- |
| Profil candidat | 12 mois après le dernier contact utile |
| Besoin employeur | 12 mois après clôture ou dernier échange utile |
| Dossier de rapprochement | 24 mois pour suivi et traçabilité des décisions |
| Invitation sans réponse | 6 mois |
| Journaux d'administration et de sécurité | 6 mois |
| Statistiques publiques | Plus longtemps seulement si agrégées et anonymisées |

Ces règles sont des contenus d'information, centralisés dans
`eures_beta/data_protection.py`. Ce lot ne constitue pas leur exécution
automatique ni une validation juridique. Il ne crée ni compte ni profil,
aucun modèle ni migration et n'efface aucune donnée.

Le brouillon candidat demeure privé à la session et expire après 30 minutes
d'inactivité, conformément à #129/#130. Expiration d'accès et purge des supports
techniques ne sont pas identiques. La conservation d'une invitation sans réponse
ne prolonge pas la validité du lien d'invitation (7 jours) ou de connexion (1 h).

## Suite de P1

- Définir l'événement métier « dernier contact utile », sa date initiale et les
  actions qui le renouvellent ; ne pas assimiler un simple chargement de page
  ou un envoi technique à un contact utile.
- Prévoir une échéance explicite pour les demandes candidat dont l'email n'est
  pas vérifié ; le délai du brouillon et la conservation du profil ne suffisent pas
  à définir ce cas nouveau.
- Définir puis implémenter suppression, anonymisation, traçabilité minimale,
  traitement des relations et politique des sauvegardes. Ne pas traiter une
  suppression de profil comme une suppression aveugle de tous les comptes.
- Compléter les mentions sur le responsable de traitement, la base juridique
  et les modalités d'effacement avant la collecte réelle de nouveaux profils.
- Actualiser le paragraphe « périmètre actuel » quand le stockage durable et
  la vérification email seront activés ; ne pas annoncer le matching comme actif.

## Vérifier

`make privacy-test` vérifie les langues malgré un cookie contradictoire, les
durées, les limites annoncées, le contact et les liens, l'accès public hors démo,
les méthodes autorisées et l'absence d'écriture/session. `make test` couvre les
liens des parcours existants ; `make format-html-check`, `make format-check`,
`make translations-check` et `make translations-compile` complètent la vérification.

Recette locale : `make run PORT=9034`, puis `/privacy/?lang=fr`, `en` ou `de`.
Aucune mise en production ni fusion ; celles-ci restent des opérations distinctes.
