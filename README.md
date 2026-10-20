# Squelette Django

Socle technique minimal : Python 3.12, Django 5.2 LTS, PostgreSQL 17 et Bootstrap 5.3.8.

- `/` : page neutre rendue par un template Django, avec Bootstrap servi localement.
- `/admin/` : administration native Django (utilisateurs et groupes).
- Aucun modèle, rôle, parcours, service externe ou habillage métier ajouté.
- Aucune migration applicative : seules les migrations natives Django sont utilisées.

## Organisation du code

`config/` contient les réglages et les points d’entrée du projet Django.
`match_europe/` est le paquet Python destiné aux futures applications métier ;
il regroupe déjà les templates partagés, les statiques et les tests du socle.
Son nom suit la convention Python des modules en minuscules avec underscores.
Il ne constitue pas à lui seul une application Django à inscrire dans
`INSTALLED_APPS`. Les futures applications pourront y vivre sous la forme
`match_europe.nom_application`.

```text
config/
match_europe/
    __init__.py
    templates/
    static/
    tests.py
manage.py
```

## Démarrage local

Prérequis : Python 3.12 et PostgreSQL 17 démarré. Créer une base et un rôle locaux
(le mot de passe est demandé interactivement) :

```sh
createuser --pwprompt skeleton
createdb --owner=skeleton skeleton
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
```

Dans `.env`, renseigner `PGPASSWORD` et une clé `DJANGO_SECRET_KEY` générée avec :

```sh
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

Entourer les valeurs de guillemets simples pour les charger avec le shell.
Le fichier `.env` est ignoré par Git et n'est pas chargé automatiquement par Django :

```sh
set -a
source .env
set +a
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Ouvrir <http://127.0.0.1:8000/> puis `/admin/` pour se connecter.
Les comptes et sessions utilisent exclusivement PostgreSQL.

## Vérifications

Avec le même environnement chargé :

```sh
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
```

Pour les tests, le rôle PostgreSQL doit pouvoir créer la base temporaire
`test_skeleton` (privilège `CREATEDB` réservé au rôle local de test).
Les tests contrôlent la page Bootstrap, la protection de l'administration et
l'accès d'un superutilisateur avec une véritable base PostgreSQL.

## Limites

`runserver` est réservé au développement. Le serveur WSGI et les statiques sont
décrits ci-dessous ; chaque déploiement doit encore configurer HTTPS, ses variables
propres à l'environnement et examiner les résultats de `check --deploy`.
`DJANGO_DEBUG` est désactivé par défaut ; une clé secrète est obligatoire.

Bootstrap est conservé sous `match_europe/static/vendor/bootstrap/`, avec sa licence MIT
incluse dans ce dossier. Aucun JavaScript ni outil de compilation frontend.

## Exécution avec un serveur applicatif

Avec les variables de connexion PostgreSQL, `DJANGO_SECRET_KEY` et
`DJANGO_ALLOWED_HOSTS` renseignées :

```sh
python manage.py migrate --noinput
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 1
```

WhiteNoise sert les fichiers statiques collectés, y compris Bootstrap et
l’administration, avec `DJANGO_DEBUG=0`. Aucun stockage persistant de documents
utilisateur n’est configuré par ce socle.

Pour un environnement HTTPS, définir `DJANGO_HTTPS=1` et les origines exactes
dans `DJANGO_CSRF_TRUSTED_ORIGINS`. `DJANGO_TRUST_PROXY=1` n’est approprié que si
le proxy de confiance remplace `X-Forwarded-Proto` et constitue le seul accès
à l’application. `PGSSLMODE` permet de configurer le mode TLS PostgreSQL.
Les domaines, comptes et procédures propres aux environnements restent dans
les dépôts privés de déploiement.

`GET /health/` vérifie la connexion PostgreSQL : réponse vide `204` si elle
fonctionne, `503` sinon. Cette route n’est pas mise en cache et reste accessible
en HTTP pour les sondes internes, même lorsque les autres pages redirigent
vers HTTPS.

La sonde est traitée avant les middlewares qui valident le nom d’hôte : un
orchestrateur peut ainsi utiliser l’adresse IP éphémère de l’instance. Seul le
chemin exact `/health/` bénéficie de ce traitement ; sa réponse ne contient ni
nom d’hôte ni URL. Les autres routes conservent `ALLOWED_HOSTS` et leurs contrôles
habituels.
