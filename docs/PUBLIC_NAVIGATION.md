# Navigation publique

Les menus utilisent les noms de routes Django : accueil à `/`, candidat à
`/candidate/`, statistiques à `/statistics/`, projet à `/project/` et journal à
`/journal/`. Les trois dernières pages affichent une annonce « en construction »
en FR/EN/DE, avec retour à l’accueil et choix de langue. Elles ne collectent aucune
donnée et ne simulent ni statistiques ni contenu éditorial.

Les anciennes adresses des formulaires sont déclarées uniquement dans les routes
de compatibilité. Django `RedirectView` les redirige en HTTP 301 vers les routes
canoniques, en préservant la chaîne de requête. Seules les lectures GET/HEAD sont
acceptées ; aucune écriture n’est redirigée. Les contrôles d’accès du parcours
candidat restent appliqués à destination.

Les redirections historiques des pages employeur restent limitées à la liste
existante des anciennes pages autorisées. Les routes métier employeur et les
versions d’import ne sont pas supprimées dans ce nettoyage.

La racine appartient uniquement à l’accueil. Le tableau de bord conserve sa route
nommée à `/dashboard/` et ses protections.

Vérifications : `make test`, `make check`, `make format-check`,
`make format-html-check`, `make format-js-check`, `make check-js` et
`make translations-check`.
