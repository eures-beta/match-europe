# Squelette Django

Socle technique minimal : Python 3.12, Django 5.2 LTS, PostgreSQL 17 et Bootstrap 5.3.8.

- `/` : page neutre rendue par un template Django, avec Bootstrap servi localement.
- `/admin/` : administration native Django (utilisateurs et groupes).
- Aucun modèle, rôle, parcours, service externe ou habillage métier ajouté.
- Aucune migration applicative : seules les migrations natives Django sont utilisées.

## Organisation du code

`config/` contient les réglages et les points d’entrée du projet Django.
`eures_beta/` est le paquet Python destiné aux futures applications métier ;
il regroupe déjà les templates partagés, les statiques et les tests du socle.
Son nom suit la convention Python des modules en minuscules avec underscores.
Il ne constitue pas à lui seul une application Django à inscrire dans
`INSTALLED_APPS`. Les futures applications pourront y vivre sous la forme
`eures_beta.nom_application`.

Ce dépôt utilise une seule configuration Django, dans `config/`, et un seul
`manage.py`, à la racine. Les dépendances et les commandes locales sont également
centralisées à la racine (`requirements.txt` et `Makefile`). Ne pas créer de second
projet dans `eures_beta/` : les futurs parcours s’ajoutent comme applications dans
ce paquet, puis sont déclarés dans `config/settings.py` et `config/urls.py`.
Les réglages du socle pour PostgreSQL, HTTPS, les statiques et la sonde restent
communs aux environnements. Aucun mode démonstration ni compte fictif n’est
activé par cette étape.

```text
config/
eures_beta/
    __init__.py
    templates/
    static/
    tests.py
manage.py
```

## Recettes jetables de pull requests

Une personne ayant le droit d’écriture peut demander une recette avec le label
`recette 24h` ou `recette 7j`. Le dernier label ajouté remplace l’autre. Les nouveaux
commits et rebases redéploient le code sans changer l’URL ni vider la base, et sans
repousser l’échéance. Retirer puis remettre le label recrée une base vide.
Les migrations proposées par une PR peuvent toutefois transformer les données de test.

Un commentaire automatique donne l’URL, le commit déployé et l’expiration. La
fermeture de la PR ou le retrait du label supprime la recette ; un contrôle toutes
les deux heures supprime les recettes expirées. Les données sont fictives et
jetables. Les PR provenant de forks ne sont pas déployées automatiquement.

L’activation et l’exploitation du contrôleur sont documentées dans le
[dépôt privé de déploiement](https://github.com/eures-beta/match-europe-deploy-clever).

## Démarrage local

`make help` présente les raccourcis du Makefile : `make install`, `make run`,
`make test`, `make check`, `make migrate` et `make dbshell` (SQL interactif via
`psql`). Les commandes Django chargent le fichier shell `.env` local s’il existe.
Créer le rôle et la base puis renseigner `.env` comme indiqué ci-dessous.
`PYTHON`, `HOST`, `PORT` et `TEST_ARGS` sont personnalisables. Pour tester plusieurs
worktrees en parallèle, choisir des `PGDATABASE` distincts dans leurs `.env`.

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

Bootstrap est conservé sous `eures_beta/static/vendor/bootstrap/`, avec sa licence MIT
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

## Formatage Python

`make install-quality` installe la version de Black épinglée dans un environnement
isolé. `make format` applique le formatage ; `make format-check` le vérifie sans
modifier les fichiers. Python 3.12 est requis pour cet outillage. Les guillemets
existants sont conservés pour réduire le bruit et préserver les adaptations FT.

Le workflow **Qualité Python**, contrôle **Black**, exécute cette vérification à
chaque push et pull request, sans secret ni dépendance applicative. Pour bloquer
les fusions, rendre **Black** obligatoire dans les règles de protection de `main`
et appliquer la règle aux administrateurs sans contournement. Ce réglage GitHub
n’est pas modifié par cette PR. Les protections des dépôts privés d’organisation
nécessitent un abonnement GitHub compatible. Black contrôle le format Python,
pas les erreurs métier, la sécurité, les templates ou le JavaScript.
