# Référentiel des métiers

Ce paquet fournit la recherche locale dans les références ESCO et ROME. `catalog.py` lit le catalogue ; `views.py` expose la recherche au site. Ce service partagé n’est pas une application avec des modèles et tables métier propres. Les données versionnées, outils de maintenance et tests sont séparés ci-dessous. Voir [la maintenance du catalogue](../../docs/OCCUPATION_CATALOG_MAINTENANCE.md).

## Contenu de ce dossier

### Dossiers

- [data/](data/) — - `occupations.json.gz` : **3 039 métiers ESCO 1.2.1**, FR/EN/DE, intitulés,   synonymes, descriptions, groupes ISCO et relations hiérarchiques du pilier métiers.
- [tests/](tests/) — Ces tests vérifient le catalogue de métiers et son API.
- [tools/](tools/) — `build_catalog.py` construit un catalogue depuis des archives locales ; `validate_catalog.py` vérifie son contenu et produit un rapport.

### Fichiers

- [__init__.py](__init__.py) — Identifie ce dossier comme un paquet Python.
- [catalog.py](catalog.py) — Charge et interroge les références locales ESCO et ROME.
- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [views.py](views.py) — Traite les requêtes HTTP et prépare les réponses de ce domaine.

[Remonter au dossier parent](../).
