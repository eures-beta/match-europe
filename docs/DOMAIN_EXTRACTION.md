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

L’extraction est progressive : employeurs/imports et rapprochements restent
encore dans `journeys` à cette étape. Ses migrations historiques restent requises.
