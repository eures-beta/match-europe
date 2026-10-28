# Accueil candidat — reprise du 28 octobre 2026

Branche `codex/candidate-landing-main`, désormais basée sur la pile de découpage
métier puis de traduction. La version d’origine reste conservée dans la PR #65.
Reprise ciblée de l’écran validé le 26 octobre (`7e6689e`), sans reprendre
l’ancienne pile de PR. Un seul template Django dans
`eures_beta/candidates/templates/candidates/landing.html`, statiques dédiés dans
`eures_beta/candidates/static/candidate/`, tests dans `eures_beta/candidates/tests/`.
Les textes candidat et ceux de l’en-tête, navigation, pied de page, accessibilité
et notices JavaScript utilisent gettext (catalogues FR/DE, sources anglaises).

La vue et ses deux routes appartiennent à `eures_beta.candidates`. Les protections
d’accès partagées du prototype sont dans `eures_beta/demo_access.py` ; ce raccordement
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

Le générateur candidat et son dictionnaire JSON trilingue ont été retirés :
le template unique et les catalogues gettext sont les sources de référence.
Après modification des textes, maintenir les `.po`, exécuter
`make translations-compile`, puis `make test`. La CSS de base et les logos
institutionnels restent des ressources partagées ; les fichiers ne sont pas dupliqués.

La comparaison avant/après consolidation couvre tous les textes, liens et
attributs des trois pages rendues. Les tests couvrent également le choix de
langue malgré un cookie différent et les notices utilisées par JavaScript.

Validation historique de la version initiale du 28 octobre : 165 tests Django sur PostgreSQL réussis ; contrôle
Django, absence de migrations, collecte des statiques et Black réussis. Après
raccordement gettext : quatre tests candidat repassés avec succès. Navigateur :
FR → EN → DE → FR, logos et activation CV par Entrée vérifiés sur la recette
locale ; contrôle visuel à la largeur de la fenêtre observée, sans audit WCAG
complet ni validation multi-appareils. Ces vérifications précèdent la reprise en PR.

Validation après consolidation : 187 tests PostgreSQL réussis sur la pile,
catalogues compilés, Black, contrôles Django/migrations et collecte des statiques
réussis. Comparaison des textes, liens et attributs rendus FR/EN/DE identique à
la version avant consolidation. Aucune nouvelle collecte de données ni activation
d’un service externe.
