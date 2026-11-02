# Workflows GitHub Actions

Les fichiers YAML déclenchent les contrôles Python, HTML, JavaScript, traductions et tests PostgreSQL. Les relais de production et de recettes transmettent les événements au dépôt privé de déploiement. Les noms, événements et permissions se lisent dans chaque workflow ; les valeurs des secrets ne sont pas versionnées ici.

## Contenu de ce dossier

### Fichiers

- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [black.yml](black.yml) — Vérifie le formatage des sources Python avec Black.
- [javascript.yml](javascript.yml) — Vérifie le format et la syntaxe JavaScript.
- [preview-relay.yml](preview-relay.yml) — Transmet les événements de recettes au dépôt privé de déploiement.
- [preview-request.yml](preview-request.yml) — Reçoit les demandes de recettes jetables liées aux PR.
- [production-relay.yml](production-relay.yml) — Transmet la validation de main au déploiement privé de production.
- [ready-for-production-check.yml](ready-for-production-check.yml) — Vérifie traductions, configuration et tests PostgreSQL avant déploiement.
- [templates.yml](templates.yml) — Vérifie le format et la structure des templates Django.

[Remonter au dossier parent](../).
