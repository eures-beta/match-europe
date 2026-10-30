# Match Europe

Match Europe est un service commun à [France Travail](https://www.francetravail.fr/)
(France), au [Forem](https://www.leforem.be/) (Wallonie, Belgique) et à
l’[ADEM](https://adem.public.lu/) (Luxembourg), dans le réseau EURES.

Il facilite le recrutement et la mobilité professionnelle entre pays européens :
rapprocher candidats et employeurs, préparer leur mise en relation avec les
conseillers et leur permettre d’échanger dans une messagerie de confiance.
Le service est en cours de développement.

## Développement local

Prérequis : Python 3.14 et PostgreSQL démarré, avec un rôle autorisé à créer des bases.
Copier `.env.example` en `.env`, puis renseigner `DJANGO_SECRET_KEY` et les
paramètres PostgreSQL (`PGUSER`, `PGPASSWORD`, `PGDATABASE`, `PGHOST`, `PGPORT`).
Pour essayer le prototype localement sans écrire dans AGLAE, ajouter :

```dotenv
ME_DEMO_MODE=1
ME_EMPLOYER_DEV_ACCESS=1
ME_EMPLOYER_EMAIL_LOCAL=1
ME_LOCAL_REVIEW_ONLY=1
```

```bash
make install-test
make db-create
make migrate
make seed-demo
make run
```

Ouvrir [localhost:8000](http://127.0.0.1:8000/). `make test` lance les tests ;
`make help` présente les autres commandes.

Pour aller plus loin : [guide de développement détaillé](docs/DEVELOPPEMENT.md).

## Contenu de ce dépôt de code

### Dossiers

- [.github/](.github/) — Configure les contrôles et relais automatisés sur GitHub.
- [clevercloud/](clevercloud/) — Regroupe les hooks génériques de construction et de démarrage Clever Cloud.
- [config/](config/) — Contient la configuration unique, les routes et les points d’entrée Django.
- [docs/](docs/) — Rassemble les guides, décisions et explications détaillées du projet.
- [eures_beta/](eures_beta/) — Contient les applications métier Django, les ressources communes et les traductions.
- [requirements/](requirements/) — Sépare les dépendances Python applicatives, de test et de qualité.

### Fichiers

- [.djlintrc](.djlintrc) — Configure l’indentation et le formatage des templates avec djLint.
- [.env.example](.env.example) — Donne un exemple de configuration locale sans identifiants réels.
- [.gitattributes](.gitattributes) — Définit les attributs Git appliqués aux fichiers du dépôt.
- [.gitignore](.gitignore) — Exclut de Git les environnements locaux, secrets et fichiers générés.
- [.prettierignore](.prettierignore) — Exclut du formatage JavaScript les fichiers qui ne doivent pas être retraités.
- [.prettierrc.json](.prettierrc.json) — Configure le style JavaScript appliqué par Prettier.
- [.python-version](.python-version) — Indique la version de Python attendue pour ce projet.
- [AGENTS.md](AGENTS.md) — Définit les consignes de travail et de maintenance destinées aux agents.
- [gunicorn.conf.py](gunicorn.conf.py) — Configure le serveur WSGI Gunicorn.
- [HANDOFF.md](HANDOFF.md) — Conserve les travaux documentés, validations datées et limites connues.
- [Makefile](Makefile) — Expose les commandes réutilisables de développement, test et maintenance.
- [manage.py](manage.py) — Point d’entrée unique des commandes de gestion Django.
- [package-lock.json](package-lock.json) — Verrouille les versions exactes des dépendances JavaScript.
- [package.json](package.json) — Déclare l’outillage JavaScript et ses dépendances de développement.
- [pyproject.toml](pyproject.toml) — Configure notamment le formatage Python du projet.
- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [requirements.txt](requirements.txt) — Point d’entrée des dépendances Python applicatives.
