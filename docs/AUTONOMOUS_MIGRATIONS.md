# Migrations autonomes : deux déploiements obligatoires

La migration `employers.0001_autonomous_schema` crée directement les sept modèles
employeur actuels et leurs contraintes. Elle ne dépend que des applications
Django intégrées. Les noms physiques `journeys_employer*` restent inchangés.
Les applications candidat et documents n'ont actuellement aucun modèle.

## Premier déploiement : transition, avec les archives encore présentes

La première PR ajoute cette migration avec un attribut transitoire `replaces`
reconnaissant les 36 anciennes migrations. Une base à jour enregistre le nouveau
marqueur sans DDL ni changement des données métier. Une base en retard termine
son ancien historique, avec son nettoyage et ses garde-fous. Une base neuve crée
directement les sept tables actuelles.

Déployer cette première version seule et laisser le déploiement habituel
exécuter `migrate`. Vérifier sur **toutes les bases à conserver** :

1. `employers.0001_autonomous_schema` est marquée appliquée ;
2. le site démarre, les pages FR/EN/DE et les imports fonctionnent ;
3. les données, sessions et habilitations conservées sont inchangées.

## Second déploiement : suppression des archives

Cette seconde PR supprime `migration_history`, les anciens labels installés,
les anciennes migrations et leurs tests. Elle retire `replaces` de la migration
autonome, **sans changer son nom ni ses opérations**.

Ne fusionner cette PR qu'après confirmation du premier déploiement. Après fusion
de sa base, la retargeter vers `main`, vérifier son diff puis la déployer par la
procédure habituelle. Une base passée par la transition conserve ses tables et
données ; une installation neuve reste possible sans aucun ancien modèle.

Si une base existante n'a pas le marqueur autonome, la migration s'arrête avant
toute création de table et demande de déployer d'abord la version de transition.
Ne pas contourner ce garde-fou avec `--fake` ou une réinitialisation.

Conserver une sauvegarde récente avant les déploiements. Les commandes et accès
propres aux environnements restent dans le dépôt privé de déploiement.

Les anciennes lignes de `django_migrations` peuvent rester : elles n'exécutent
aucun code et ne recréent aucun modèle. Ne pas les effacer manuellement.
Ne pas lancer une migration inverse comme rollback : cela pourrait supprimer
les tables actuelles et leurs données.

## Vérifications locales

- `make migrations-test` : installation neuve, données d'une base passée par
  la transition et refus d'une base ayant sauté cette étape.
- `make test` : suite complète PostgreSQL dans une base de test locale dédiée.
- `make check` : contrôles Django et absence de migration manquante.
- `make migrations` : état des migrations de la base locale configurée.

Les tests utilisent le chargeur Django normal et ne dépendent plus d'archives.

Référence : [transition après consolidation dans Django](https://docs.djangoproject.com/en/6.1/topics/migrations/#squashing-migrations).
