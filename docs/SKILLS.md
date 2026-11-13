# Compétences et catalogue ESCO

Les compétences sont intégrées aux parcours candidat et employeur dans tous les
environnements. Les anciennes pages autonomes `/skills-pilot/` ont été retirées ;
il ne faut ni les recréer ni lancer un serveur de démonstration distinct.
Les réponses sont soumises à validation serveur, puis conservées selon le contrat
du parcours concerné. Voir [le parcours candidat](CANDIDATE_JOURNEY.md) et
[les compétences intégrées](CONTINUOUS_JOURNEYS.md).

## Catalogue éditorial

Le catalogue comporte 50 métiers ESCO : 49 fiches et une variante nettoyage.
Chaque fiche propose huit compétences clés et quatre savoir-être. Ces sélections
sont éditoriales ; elles ne constituent ni un classement statistique ni une
équivalence ESCO/ROME. Les compétences déclarées ne sont pas inférées d'un métier.
Voir [la liste et les identifiants](SKILLS_CATALOGUE_50.md).

Les concepts et libellés officiels FR/EN/DE sont fournis par ESCO 1.2.1.
Les liens métier–compétence et les associations éditoriales sont distingués.
Le cache du catalogue est propre à chaque processus : redémarrer les processus
après remplacement des données. Le chargement du catalogue ne fait aucun appel
Albert ou réseau ; les suggestions Albert relèvent d'un service distinct.

## Données

`skills/data/occupation_skills_sources.json` contient les concepts officiels ESCO
1.2.1 utilisés et leurs libellés FR/EN/DE, descriptions, sources, empreintes et
relations métier–compétence. `occupation_skills.json` contient la sélection éditoriale,
son ordre et les rubriques. Le chargement ne dépend d’aucun réseau.

Les huit compétences clés de chaque fiche ont une relation officielle ESCO avec
le métier correspondant. Les concepts utilisés comme savoir-être sont officiels,
mais leur proposition pour un métier est souvent éditoriale ; l’origine et la
présence éventuelle d’un lien officiel sont conservées. « Essential » dans ESCO
ne veut pas dire « obligatoire dans toute offre ». La rubrique savoir-être est
une présentation de Match Europe, pas une nouvelle classification officielle.

Reconstruction reproductible : `make skills-pilot-build`, avec
`CATALOG_SOURCES` pointant vers les trois archives CSV officielles ESCO 1.2.1.
Les empreintes doivent correspondre à celles épinglées dans les données.
La commande écrit uniquement `.runtime/skills-pilot-staging` : comparer ces deux
fichiers aux fichiers versionnés avant toute promotion. Une nouvelle édition,
une modification du périmètre ou une réécriture des libellés demande une revue.

Cette application utilise la classification ESCO de la Commission européenne.
Les choix éditoriaux sont propres à Match Europe. Voir les
[archives officielles](https://esco.ec.europa.eu/en/use-esco/download) et les
[conditions de réutilisation](https://esco.ec.europa.eu/en/about-esco/faq?page=1).

## Maintenance et vérification

Les noms historiques des commandes de maintenance sont conservés ; ils ne
signifient pas qu'un parcours autonome est encore disponible.

- `make skills-pilot-audit CATALOG_SOURCES=/chemin/archives` : comparer concepts,
  libellés et relations aux trois archives officielles épinglées, sans réseau.
- `make skills-pilot-build CATALOG_SOURCES=/chemin/archives` : reconstruction
  en staging, à comparer aux données versionnées avant toute promotion.
- `make test TESTS=eures_beta.skills.tests.test_skills_pilot` : contrôles du catalogue et de la sélection.
- `make test TESTS=eures_beta.candidates.tests.test_skill_project`, `make test TEST_ARGS='-k continuous -k skill_source_prepare'` : intégration aux parcours.
- `make test`, `make check`, `make translations-check` : validation transverse.

Une modification de la sélection ou des libellés exige une revue éditoriale.
Les tests utilisent des données locales et des services externes simulés.
