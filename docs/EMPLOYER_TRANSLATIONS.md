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
série. La page technique locale de diagnostic Push et son JavaScript français
restent un chantier distinct ; elle n’est pas exposée dans la démonstration partagée.
