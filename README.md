# match-europe

A minimal Django application using PostgreSQL and Bootstrap.

## Run with Docker Compose

Install Docker Compose, then start the app and database:

```sh
docker compose up --build
```

Open [http://localhost:8000](http://localhost:8000). The application applies
database migrations before starting. Stop the services with `Ctrl+C`; use
`docker compose down -v` to also remove the local database data.

## Run locally

Install PostgreSQL and Python 3.12+, create a database, and install the
dependencies:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export DB_NAME=match_europe DB_USER=postgres DB_PASSWORD=postgres DB_HOST=localhost
python manage.py migrate
python manage.py runserver
```

The local PostgreSQL server must have a database named `match_europe` and
accept connections from the configured user.
