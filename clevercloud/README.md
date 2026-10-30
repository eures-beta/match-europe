# Contrat de lancement Clever Cloud

Ce dossier regroupe uniquement les étapes génériques de l’application, comme le
[dossier Clever Cloud des Emplois](https://github.com/gip-inclusion/les-emplois/tree/main/clevercloud).
Il ne contient aucun secret, identifiant de ressource ou domaine d’environnement.

| Variable Clever Cloud | Commande proposée |
| --- | --- |
| `CC_POST_BUILD_HOOK` | `./clevercloud/post_build.sh` — collecte des statiques |
| `CC_PRE_RUN_HOOK` | `./clevercloud/pre_run.sh` — migrations |
| `CC_RUN_COMMAND` | `./clevercloud/run.sh` — Gunicorn |

`http.json` impose HTTPS et UTF-8. Les hooks s’exécutent à la racine du dépôt,
avec le Python du runtime ; `PYTHON` permet de choisir un interpréteur local.
Le lancement conserve un worker et le port 9000 par défaut.

Les scripts ne s’activent pas par leur seule présence : les variables des hooks
doivent pointer vers eux, selon la [documentation des hooks](https://www.clever.cloud/developers/doc/develop/common-configuration/build-hooks/).
Cette PR ne modifie aucune application hébergée.
Le contrôleur privé conserve la création des ressources, les secrets, les domaines,
les recettes jetables et le déploiement automatique. Lors du raccordement des hooks,
conserver les réglages validés du prototype partagé et les protections HTTPS,
CSRF et d’accès aux données. Les environnements sont configurés dans le dépôt privé.

Pour reproduire les étapes localement avec le `.env` personnel :

```bash
make clever-post-build
make clever-pre-run
make clever-run
```

La dernière commande écoute uniquement sur loopback en usage local via Make.
Les tâches planifiées et le chargement de secrets propres aux Emplois ne sont pas
repris : Match Europe n’a pas besoin de reproduire leur infrastructure complète.

## Contenu de ce dossier

### Fichiers

- [http.json](http.json) — Configure le comportement HTTP attendu par Clever Cloud.
- [post_build.sh](post_build.sh) — Exécute le hook de préparation après construction de l’application.
- [pre_run.sh](pre_run.sh) — Exécute les opérations requises avant le démarrage de l’application.
- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [run.sh](run.sh) — Lance le serveur applicatif via le hook Clever Cloud.

[Remonter au dossier parent](../).
