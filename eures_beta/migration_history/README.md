# Compatibilité des migrations historiques

Ce paquet conserve l’historique de l’ancienne application `journeys`, dont le label technique reste nécessaire aux bases existantes. Il ne contient pas de modèles métier actifs : ceux-ci vivent désormais dans les applications spécialisées. Ne pas supprimer cet historique parce que le dossier `journeys` a disparu. Voir [le découpage des domaines](../../docs/DOMAIN_EXTRACTION.md).

## Contenu de ce dossier

### Dossiers

- [migrations/](migrations/) — Ces migrations retracent la création des objets historiques, puis le transfert de leur état vers les nouvelles applications.

### Fichiers

- [__init__.py](__init__.py) — Identifie ce dossier comme un paquet Python.
- [apps.py](apps.py) — Déclare l’application auprès de Django et son identité technique.
- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.

[Remonter au dossier parent](../).
