# Accueil candidat — reprise du 28 octobre 2026

Branche `codex/candidate-landing-main`, désormais basée sur la pile de découpage
métier puis de traduction. La version d’origine reste conservée dans la PR #65.
Reprise ciblée de l’écran validé le 26 octobre (`7e6689e`), sans reprendre
l’ancienne pile de PR. Templates Django dans `eures_beta/templates/candidate/`,
statiques dédiés dans `eures_beta/static/candidate/` et textes candidat traduits
par gettext Django (catalogues FR/DE, sources anglaises).

La vue et ses deux routes appartiennent à `eures_beta.candidates`. Les protections
d’accès partagées du prototype restent réutilisées depuis `journeys` ; ce raccordement
ne crée pas un nouveau système d’authentification et ne modifie pas les pages.

Entrée : `/candidate/?lang=fr` (FR/EN/DE). L’ancien lien
`/forms/eures-beta/candidate?lang=fr` reste utilisable, notamment depuis
l’accueil employeur. Les protections de démonstration du main sont conservées :
404 hors démo, HTTPS en démo partagée, accès local explicite sinon ; GET/HEAD
uniquement. Aucun modèle ni migration, aucune API employeur activée sur cet écran.

Les choix CV, LinkedIn et saisie manuelle affichent une notice de simulation.
La connexion candidat reste à préparer. Aucun upload, stockage de profil,
consultation LinkedIn ou service externe. La coque et les logos officiels
sont repris des templates employeur actuels sans modification des images.
Les liens historiques projet/journal/statistiques de la coque restent hérités ;
leurs destinations ne sont pas implémentées dans ce lot. La notice de protection
des données reste celle du prototype employeur, à revoir avant collecte candidat.

Génération : `node scripts/employer-ui/build-candidate.cjs` depuis la racine.
Le générateur lit les templates employeur actifs et produit les trois templates
candidat. Après modification des textes : maintenir `candidate-copy.json`, les
catalogues gettext et recompiler les `.mo`. `make employer-pages-build` inclut
la génération candidat ; la génération employeur historique reste dans `build/`.

Validation du 28 octobre : 165 tests Django sur PostgreSQL réussis ; contrôle
Django, absence de migrations, collecte des statiques et Black réussis. Après
raccordement gettext : quatre tests candidat repassés avec succès. Navigateur :
FR → EN → DE → FR, logos et activation CV par Entrée vérifiés sur la recette
locale ; contrôle visuel à la largeur de la fenêtre observée, sans audit WCAG
complet ni validation multi-appareils. Aucun push, PR, fusion ou déploiement.
