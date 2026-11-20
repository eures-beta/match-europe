# Référentiels métiers partagés

Ce paquet fournit les métiers ESCO, fiches ROME, appellations OGR et leurs
correspondances aux parcours candidat et employeur. Il n’attribue aucune
compétence aux personnes et ne calcule pas de matching.

- [data/](data/) : les quatre JSON publics, leurs sources et empreintes.
- [management/](management/) : commandes Django de mise à jour explicite.
- [tools/](tools/) : lecture des exports, reconstruction, validation et mesures.
- [tests/occupations/](../../tests/occupations/) : intégrité, recherche et importateurs sans réseau externe.
- [catalog.py](catalog.py) : chargement en cache, recherches multilingues et
  reconnaissance commune des références sans regex à retours arrière ambigus.
- [unified.py](unified.py) : regroupements exacts non ambigus ; lecture vérifiée
  du tableau de correspondances en flux, sans seconde copie complète de ROME/OGR.
- [views.py](../www/occupations/views.py) : interface HTTP de recherche de métiers.
- [test_picker.cjs](../../tests/occupations/test_picker.cjs) : tests JavaScript du sélecteur.
- [__init__.py](__init__.py) : déclaration du paquet Python.

Voir la [procédure de maintenance](../../docs/OCCUPATION_CATALOG_MAINTENANCE.md).
Les tests des références et des recherches sont décrits dans [tests/occupations/](../../tests/occupations/).
La limite HTTP de 150 caractères est conservée ; voir le [triage CodeQL](../../docs/CODEQL_TRIAGE.md).


## Retrait du parcours autonome — 9 novembre 2026

Après intégration aux formulaires candidat et employeur (#158), les routes
`/skills-pilot/` et leurs écrans sont supprimés. Les catalogues, leurs outils
de maintenance et le service de suggestions restent utilisés par les vrais
parcours. Aucun modèle, migration ou réponse durable n’est supprimé. Les
anciens brouillons de session ne sont plus lus ; aucune purge SQL ajoutée.


## Séparation métiers et compétences — 9 novembre 2026

Les métiers et recherches restent dans occupations ; catalogues de compétences,
suggestions et composant intégré vivent dans [skills](../skills/). Le matching est créé séparément par la PR #160. Le transfert du modèle conserve
la table PostgreSQL, les identifiants, les suggestions et les permissions.

- [Catalogue commun](../../docs/COMMON_OCCUPATION_SKILLS.md) : regroupements exacts et choix de compétences ESCO/ROME, sources et limites.
