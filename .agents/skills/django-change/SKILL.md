---
name: django-change
description: Modifier un service, un modèle ou un parcours Django de Match Europe, avec droits, stockage, migrations et validation PostgreSQL. Ne pas utiliser pour une simple édition documentaire.
---

# Changement Django

Lire les règles racine, les [décisions](../../../docs/DECISIONS.md), les
[retours pertinents](../../../docs/AGENT_FEEDBACK.md) et le guide du domaine touché.

Identifier le rôle utilisateur, les données transitoires/durables, les relations,
les effets externes et les autorisations/refus attendus. Respecter la séparation
www/domaines décrite dans [l'architecture](../../../docs/ARCHITECTURE_WEB.md).

Le nom de l'environnement et les comptes de démonstration ne conditionnent jamais
le parcours métier. Tester aussi les requêtes distantes et les adresses ordinaires
fictives dans les trois configurations, avec les frontières externes simulées.

Réutiliser les validations et services du domaine. Pour une migration, préserver
les données, identifiants et permissions ; tester les anciennes lignes et le retour
arrière quand pertinent. Ne pas modifier une migration déjà publiée.

Utiliser le .venv et la base du worktree ; [préparer PostgreSQL](../../../docs/DEVELOPPEMENT.md)
avec les cibles communes. Valider via `make check`, `make test` et les contrôles
de qualité adaptés ; sélectionner des tests avec TESTS/TEST_ARGS, sans nouvelle cible
par domaine. Voir [les dispositifs de test](../../../docs/TESTS.md).

Décrire le changement de comportement, les modèles/migrations, les données
sauvegardées et les preuves réellement exécutées. Actualiser le guide métier
et seulement les points encore utiles à la reprise, pas un journal de commandes.
