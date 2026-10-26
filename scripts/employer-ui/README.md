# Sources de génération des pages employeur

`page-source.js` fournit les gabarits et textes utilisés par
le générateur Node des pages employeur (`build.cjs`). Il est évalué avec Node pour fabriquer
les HTML ; il ne doit pas être chargé comme script de l’application Django.
Le fichier contient encore des fonctions héritées inutilisées par ce générateur ;
leur extraction ou suppression relève d’un changement distinct.

Le CSS servi au navigateur est dans `eures_beta/static/employer/site.css`.
