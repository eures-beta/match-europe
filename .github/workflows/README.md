# Workflows GitHub Actions

Les fichiers YAML déclenchent les contrôles Python, HTML, JavaScript, traductions et tests PostgreSQL. Les relais de production et de recettes transmettent les événements au dépôt privé de déploiement. Les noms, événements et permissions se lisent dans chaque workflow ; les valeurs des secrets ne sont pas versionnées ici.

## Contenu de ce dossier

### Fichiers

- [black.yml](black.yml) — Tests portant sur le formatage des sources Python avec Black.
- [javascript.yml](javascript.yml) — Tests portant sur le format et la syntaxe JavaScript.
- [preview-relay.yml](preview-relay.yml) — Transmet les événements de recettes au dépôt privé de déploiement.
- [preview-request.yml](preview-request.yml) — Reçoit les demandes de recettes jetables liées aux PR.
- [production-relay.yml](production-relay.yml) — Transmet la validation de main au déploiement privé de production.
- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [ready-for-production-check.yml](ready-for-production-check.yml) — Tests portant sur traductions, configuration et tests PostgreSQL avant déploiement.
- [templates.yml](templates.yml) — Tests portant sur le format et la structure des templates Django.

[Remonter au dossier parent](../).
