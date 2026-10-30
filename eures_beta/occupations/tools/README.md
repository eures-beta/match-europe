# Maintenance du catalogue métier

`build_catalog.py` construit un catalogue depuis des archives locales ; `validate_catalog.py` vérifie son contenu et produit un rapport. Ces outils appartiennent au domaine métiers, pas à un dossier générique de scripts à la racine. Depuis la racine : `make occupations-build`, `make occupations-validate` et `make occupations-test`. Les entrées, sorties et limites sont décrites dans [le guide de maintenance](../../../docs/OCCUPATION_CATALOG_MAINTENANCE.md).

## Contenu de ce dossier

### Fichiers

- [__init__.py](__init__.py) — Identifie ce dossier comme un paquet Python.
- [build_catalog.py](build_catalog.py) — Construit le catalogue métier à partir des sources locales.
- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [validate_catalog.py](validate_catalog.py) — Tests portant sur le catalogue métier et produit un rapport de validation.

[Remonter au dossier parent](../).
