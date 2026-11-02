# Migrations autonomes : transition en deux déploiements

## Ce qui change

`employers.0001_autonomous_schema` remplace les 36 migrations du graphe connecté
du premier prototype : `journeys`, les applications retirées, les anciens modèles
candidat/document et le transfert vers `employers`.

Ce remplacement est commun à plusieurs labels parce que les tables ont été
créées dans `journeys`, puis transférées sans copie dans les applications métier.
Consolider chaque label isolément laisserait ces dépendances et les opérations
de transfert. Les opérations finales sont explicites : création des sept modèles
employeur actuels et de leurs contraintes, sans modèle retiré ni peuplement.
Les noms physiques des tables actuelles `journeys_employer*` ne changent pas.

Le mécanisme natif `Migration.replaces` choisit le chemin :

| État de la base | Chemin utilisé |
| --- | --- |
| Installation neuve, aucune des 36 migrations appliquée | Migration consolidée ; seules les sept tables métier actuelles sont créées. |
| Ancien historique entièrement appliqué | Aucun changement de schéma ; `migrate` enregistre la consolidation comme appliquée. |
| Ancien historique partiellement appliqué | Les anciennes migrations terminent la transition, y compris le nettoyage ciblé et le refus de supprimer des données hors scénario. |

Les imports, établissements, identités, appartenances, opérations de recherche,
sessions, utilisateurs et permissions existants ne sont ni recréés ni réinitialisés
par la reconnaissance d'un historique entièrement appliqué.

## Ordre de déploiement

La transition est livrée en deux PR :

1. **Déployer la première PR seule**, avec l'historique encore présent. Le
   déploiement habituel doit exécuter `migrate`, même si aucune table métier ne
   doit changer. Une base en retard termine d'abord ses anciennes migrations.
2. Vérifier que `employers.0001_autonomous_schema` est marquée appliquée, que
   le site démarre, que les imports fonctionnent et que les données conservées
   sont inchangées. Faire ce contrôle sur tous les environnements à conserver.
3. **Déployer la seconde PR seulement après cette confirmation.** Elle retire
   l'historique, les applications de compatibilité et l'attribut `replaces`.
   Le nom de la migration autonome reste identique : elle est déjà appliquée.

Les nouvelles installations restent possibles après chacune des deux étapes.
Si la seconde version est installée sur une base existante sans le marqueur
autonome, un garde-fou bloque avant toute création de table et demande de passer
par la première version. Ne pas contourner ce contrôle.

Conserver une sauvegarde récente avant les changements de base. Les destinations
et commandes propres aux environnements restent dans le dépôt privé de déploiement.
Ne pas utiliser `--fake`, ne pas supprimer de lignes de `django_migrations` et
ne pas réinitialiser une base existante pour effectuer cette transition.

## Quand supprimer les anciens fichiers ?

Pas dans ce lot : les 36 anciennes migrations coexistent avec leur remplacement.
Après confirmation que tous les environnements conservés ont exécuté `migrate`
avec cette version, un lot distinct pourra supprimer les fichiers remplacés,
adapter les dépendances restantes et retirer `replaces`. Les paquets de
compatibilité devenus inutiles pourront alors disparaître.

Le retour au code précédent et la restauration d'une base sont deux opérations
différentes. Ne pas lancer une migration inverse de la consolidation comme
moyen de rollback : elle pourrait supprimer les tables actuelles et leurs données.

## Vérifications locales

- `make migrations-test` : base neuve, historique complet ou partiel, garde-fou
  sur les données hors scénario et anciens tests de migration.
- `make test` : suite complète PostgreSQL sur une base de test locale dédiée.
- `make check` : contrôles Django et absence de migration manquante.
- `make migrations` : état des migrations de la base locale configurée.

Les tests de l'ancien historique utilisent un chargeur réservé aux tests qui
ignore les remplacements ; les tests de consolidation utilisent le chargeur
Django normal. Aucun réglage de production ne désactive les remplacements.

Référence : [consolidation des migrations Django](https://docs.djangoproject.com/en/6.1/topics/migrations/#squashing-migrations).
