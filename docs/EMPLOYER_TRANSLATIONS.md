# Traductions des pages employeur

Les pages d’accueil, confidentialité, import et import V2 utilisent chacune un
template Django commun aux trois langues. L’enveloppe des pages de connexion est
également commune. Les anciennes URL linguistiques sont conservées ; leur langue
prime sur le cookie. La connexion utilise son paramètre `lang` existant.

Les textes source sont anglais. Les catalogues `eures_beta/locale/fr` et `de`
contiennent les traductions `.po` et leurs versions compilées `.mo`. Les textes
JSON consommés par les scripts d’import passent également par gettext, avec
échappement JavaScript pour conserver un JSON valide.

Après modification : `make translations-compile`, puis `make test`.
Pour ajouter un texte, utiliser les balises Django `translate` / `blocktranslate`
ou les fonctions gettext Python, avec un contexte si nécessaire. Conserver les
libellés d’accessibilité et les liens dans la bonne langue.

Les générateurs historiques de `scripts/employer-ui/` ne sont plus la source
des templates consolidés : ne pas recopier leur sortie sur ces fichiers. Ils
restent présents pour l’outillage historique et ne sont pas supprimés dans cette
série. Le diagnostic Push utilise désormais gettext pour sa page, ses messages
JavaScript et sa notification différée ; il reste strictement local et n’est pas
exposé dans la démonstration partagée. Les messages JavaScript du parcours
employeur ne contiennent plus de dictionnaires de traduction parallèles.

`make translations-extract` actualise les catalogues depuis le code et les
templates ; `make translations-check` refuse toute entrée vide ou encore fuzzy.
Ces contrôles, suivis de la compilation, sont exécutés dans la CI avant déploiement.
Les notifications à libellés stockés utilisent `gettext_noop` pour conserver la
clé en base et traduire à l’affichage, dans la langue de la personne qui lit.

## Lisibilité HTML

Black formate le Python. djLint, avec le profil Django, formate les templates :
`make format-html` et `make format-html-check`. La cible est 120 colonnes et une
indentation de deux espaces. Les messages gettext atomiques longs peuvent
dépasser cette cible ; les listes et blocs HTML ne restent plus minifiés.
Les dictionnaires JSON des scripts sont également indentés. Le contrôle de
format HTML est visible dans GitHub Actions, sans modification des protections
de branche. `make install-quality` installe les deux outils.

Les annonces, noms et contenus saisis ne sont pas traduits automatiquement.
Les tests de page vérifient les liens comme éléments HTML, indépendamment
des sauts de ligne du code source.
