# Traduction de l’accueil employeur

Les URL `fr.html`, `en.html` et `de.html` utilisent le même template `employer/landing.html`.
La langue de l’URL active gettext pour le rendu ; les liens gardent la langue choisie.
Les textes anglais sont marqués avec `{% translate %}` et le contexte `employer landing`.
Les traductions françaises et allemandes sont dans `eures_beta/locale/*/LC_MESSAGES/django.po`.
Après modification des catalogues, utiliser `make translations-compile` (GNU gettext requis).

Les textes, logos et mise en page existants sont conservés. Les notices historiques et
les liens métier non implémentés ne sont pas corrigés dans cette PR de traduction.
L’accueil ne dépend plus de trois fichiers HTML générés. Les autres pages et les
générateurs restent conservés : leur suppression complète demande de migrer aussi
l’import V1/V2, les notices et les structures de connexion, une page à la fois.
