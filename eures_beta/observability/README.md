# Observabilité

Mesures communes des requêtes HTTP, du SQL et des étapes métier ; aucune donnée de contenu n’est conservée.

## Contenu

- [__init__.py](__init__.py) — Déclare le paquet Python.
- [middleware.py](middleware.py) — Mesure les requêtes et installe les compteurs SQL.
- [runtime.py](runtime.py) — Partage le contexte de mesure, les étapes fixes et le diagnostic Gunicorn.
- [tests/observability/](../../tests/observability/) — Vérifie les mesures, la concurrence et la confidentialité.
- [README.md](README.md) — Explique le rôle et le contenu de ce dossier.

[Remonter au dossier parent](../).
