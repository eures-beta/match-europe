# Référentiels métiers partagés

Ce paquet fournit les métiers ESCO, fiches ROME, appellations OGR et leurs
correspondances aux parcours candidat et employeur. Il n’attribue aucune
compétence aux personnes et ne calcule pas de matching.

- [data/](data/) : les quatre JSON publics, leurs sources et empreintes.
- [management/](management/) : commandes Django de mise à jour explicite.
- [tools/](tools/) : lecture des exports, reconstruction, validation et mesures.
- [tests/](tests/) : intégrité, recherche et importateurs sans réseau externe.
- [catalog.py](catalog.py) : chargement local en cache et recherches multilingues.
- [views.py](views.py) : interface HTTP de recherche de métiers.
- [test_picker.cjs](test_picker.cjs) : tests JavaScript du sélecteur.
- [__init__.py](__init__.py) : déclaration du paquet Python.

Voir la [procédure de maintenance](../../docs/OCCUPATION_CATALOG_MAINTENANCE.md).
