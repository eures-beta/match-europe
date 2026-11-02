# Compatibilité des migrations

Ce dossier ne contient aucune fonctionnalité du site. Il conserve le graphe des
migrations déjà appliquées aux bases existantes et nécessaire aux installations
neuves.

Une migration consolidée dans `employers` remplace désormais ce graphe pour les
installations neuves. Les fichiers de ce dossier restent disponibles pendant la
transition des bases existantes. Voir [le fonctionnement et l'ordre de déploiement](../../docs/AUTONOMOUS_MIGRATIONS.md).

- `migrations/` : historique du label Django `journeys`.
- `retired/` : anciens labels `accounts`, `offers`, `matching`, `conversations`
  et `notifications`, sans modèles ni routes actifs.
- `testing.py` et les tests des sous-paquets : vérifications des transitions
  historiques sur une base PostgreSQL de test isolée.

Le nom du paquet Python a changé ; les labels Django, noms de migrations et
dépendances restent identiques. Ces petits paquets restent donc déclarés dans
`INSTALLED_APPS` pour que Django retrouve les migrations. Cela ne recrée ni
modèle métier ni table supprimée.

Le lot de rangement seul n'ajoute aucune migration et ne modifie aucune donnée.
Le retrait des tables est effectué par les migrations du lot précédent. Pour
un déploiement en deux étapes, appliquer d'abord ce retrait et vérifier le site,
puis déployer ce rangement.

Ne pas supprimer ces archives simplement parce que les tables ont disparu : les
migrations peuvent encore être utilisées par les environnements partiellement
mis à jour. Leur suppression après consolidation doit attendre la vérification
de tous les environnements conservés.

Vérifier avec `make check` et `make test`.
