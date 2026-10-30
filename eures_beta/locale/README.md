# Traductions gettext

Les textes sources sont en anglais dans le code Python et les templates Django. Les sous-dossiers `fr/` et `de/` contiennent leurs traductions : une page peut ainsi avoir un seul template pour les trois langues. Depuis la racine : `make translations-extract`, `make translations-check`, puis `make translations-compile`. Voir [l’organisation des traductions](../../docs/EMPLOYER_TRANSLATIONS.md).

## Contenu de ce dossier

### Dossiers

- [de/](de/) — Ce dossier regroupe les catalogues gettext pour le allemand.
- [fr/](fr/) — Ce dossier regroupe les catalogues gettext pour le français.

### Fichiers

- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.

[Remonter au dossier parent](../).
