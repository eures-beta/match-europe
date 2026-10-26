# Navigation de langue après déplacement des pages

La PR #38, fusionnée dans #34 au commit `23e8664`, a déplacé les pages de
`/previews/employer-landing/` vers `/employer/pages/` sans redirection des anciennes URL.
Une page française déjà ouverte conserve son ancienne adresse et ses liens relatifs :
les clics EN/DE demandent alors les anciennes URL et reçoivent une erreur 404.
Une nouvelle ouverture de `/` fonctionne, ce qui explique pourquoi les tests directs
des nouvelles adresses ne détectaient pas cette régression.

Les trois mêmes tests de navigation passent sur la tête de #15 (`dbce808`) et
échouent sur #34 avant correctif. Le premier commit de cette PR ajoute ces tests,
le second rétablit les liens avec des redirections permanentes vers les pages actuelles.
`make test-navigation` exécute ce contrôle ; il fait aussi partie de `make test`.

L’ancien préfixe n’est conservé que pour la compatibilité des liens : aucune page
n’y est servie et « preview » reste réservé aux recettes jetables dans le code actif.
Seules les douze pages publiques connues sont redirigées, sans exposition des sources.
