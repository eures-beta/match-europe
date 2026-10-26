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
