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

## Rapprochements

`matching` porte Match, Answer, les suggestions fictives, les accords et la revue
du rapprochement, ainsi que le tableau de suivi par rôle. Les permissions des
offres sont dans `offers.permissions`. Les règles métier et URL sont inchangées.

Les tables des rapprochements et réponses restent en place. La relation de la
conversation est mise à jour dans l’état Django uniquement : sa clé étrangère
physique pointe déjà sur la même table. Les tests conservent réponses, accords,
conversations et permissions dans les deux sens.

## Retrait du module métier historique

Le dossier `journeys` est supprimé. Les formulaires candidat/offre vivent dans
leurs applications, l’extraction PDF dans `documents`, les vues communes et
ressources PWA au niveau du projet. La commande `seed_demo` appartient à
`accounts`. Les tests sont rangés par application ; les scénarios transverses
et leur préparation commune restent dans le paquet du projet.

Les 18 migrations historiques sont déplacées sans changement dans
`eures_beta/migration_history/migrations`. Cette application **technique** garde
le label Django `journeys` et ne fournit aucun modèle métier. Ce label doit
rester présent pour lire `django_migrations` et les dépendances existantes.
Il n’y a aucun reset de base ni besoin de `--fake`.

Les tables physiques conservent leurs noms `journeys_*`. Supprimer ces traces
historiques demanderait une transition de schéma distincte, avec inventaire des
environnements. Ce n’est pas nécessaire pour la séparation métier et ce n’est
pas fait ici.
