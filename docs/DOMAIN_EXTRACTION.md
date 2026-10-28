# Découpage des applications Django

## Comptes

`accounts` porte les profils et rôles, jetons de connexion, contrôles d’accès et
événements d’audit liés aux acteurs. Les vues d’accès fictif gardent leurs mêmes
restrictions ; ce déplacement n’introduit pas une authentification de production.

Les tables physiques `journeys_profile`, `journeys_accesstoken` et
`journeys_event` sont conservées. Les migrations changent l’état Django avec
`SeparateDatabaseAndState`, sans créer ni supprimer de table. Les ContentType
sont réétiquetés en conservant leurs clés primaires, permissions et associations.
Un conflit de ContentType arrête la migration pour inspection.

Les tests PostgreSQL vérifient les valeurs, relations, tables et identifiants de
permissions dans les deux sens. `make migrations-create` génère les futures
migrations à relire ; `make check` vérifie qu’aucune migration n’est oubliée.

## Employeurs et imports

`employers` porte les établissements, appartenances, identités employeur,
brouillons/imports, liens de vérification et opérations de recherche simulée.
Les adaptateurs de lecture des offres, formulaires, API, pages et tests associés
vivent dans cette application. Les URL et contrôles d’accès sont conservés.

Les sept modèles utilisent leurs tables `journeys_*` existantes. L’aller-retour
de migration conserve également les imports JSON, relations UUID, appartenances,
événements et permissions. Aucun service externe n’est appelé par ces tests.

L’extraction est progressive : les rapprochements et quelques utilitaires
transverses restent dans `journeys`. Ses migrations historiques restent requises.
