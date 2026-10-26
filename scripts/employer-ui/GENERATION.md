# Génération des pages employeur

Les pages actives sont dans `eures_beta/templates/employer/`, servies sous
`/employer/pages/`. Leurs scripts, styles et logos sont dans
`eures_beta/static/employer/`. Le terme preview est réservé aux recettes jetables.

`make employer-pages-build` exécute les deux générateurs Node et écrit seulement
dans `build/employer-ui/`, ignoré par Git. Il ne remplace jamais les templates actifs.
Node est un outil de développement, pas une dépendance du serveur Django.

Ces générateurs historiques combinent le gabarit de page conservé séparément, les textes JSON FR/EN/DE et un exemple AGLAE daté.
Le snapshot sert au formulaire de démonstration, pas à remplir PostgreSQL.
Les pages V2 ont évolué depuis : ces générateurs ne reproduisent pas toutes leurs
modifications. Comparer leurs sorties avant toute reprise manuelle ; ne pas les
copier automatiquement dans les templates. Les JSON restent des sources utiles,
pas des données utilisateur.

Les logos ont été déplacés sans modifier leurs octets. Le diagnostic Push reste
réservé au développement local autorisé et interdit en démonstration partagée.
