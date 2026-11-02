# Compatibilité des migrations

Ce dossier ne contient aucune fonctionnalité du site. Il conserve le graphe des
migrations déjà appliquées aux bases existantes et nécessaire aux installations
neuves.

- `migrations/` : historique du label Django `journeys`.
- `retired/` : anciens labels `accounts`, `offers`, `matching`, `conversations`
  et `notifications`, sans modèles ni routes actifs.
- `testing.py` et les tests des sous-paquets : vérifications des transitions
  historiques sur une base PostgreSQL de test isolée.

Le nom du paquet Python a changé ; les labels Django, noms de migrations et
dépendances restent identiques. Ces petits paquets restent donc déclarés dans
`INSTALLED_APPS` pour que Django retrouve les migrations. Cela ne recrée ni
modèle métier ni table supprimée.

Le rangement ne contient aucune nouvelle migration et ne modifie aucune donnée.
Le retrait des tables est effectué par les migrations du lot précédent. Pour
un déploiement en deux étapes, appliquer d'abord ce retrait et vérifier le site,
puis déployer ce rangement.

Ne pas supprimer ces archives simplement parce que les tables ont disparu : les
migrations du parcours employeur et des autres applications dépendent encore de
leur historique. Une éventuelle consolidation globale des migrations est un
travail distinct, qui doit aussi couvrir les installations neuves.

Vérifier avec `make check` et `make test`.
