# Mise à jour par source officielle

- [sync_esco.py](sync_esco.py) : métiers ESCO dans les trois langues.
- [sync_rome.py](sync_rome.py) : fiches ROME et appellations OGR d’une même édition.
- [sync_esco_rome.py](sync_esco_rome.py) : relations officielles entre ESCO et ROME.
- [_sync_catalog.py](_sync_catalog.py) : options communes, erreurs et bilan.
- [__init__.py](__init__.py) : déclaration du paquet.

Les commandes sont exposées par `make occupations-sync-esco`,
`make occupations-sync-rome` et `make occupations-sync-esco-rome`.
Voir la [procédure de maintenance](../../../../docs/OCCUPATION_CATALOG_MAINTENANCE.md)
et le [dossier parent](../).
