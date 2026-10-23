# Prototype Django — branche de conservation

Le point d’entrée à la racine sert désormais le prototype conservé dans
`match_europe/`, avec Python 3.12, Django 5.2 LTS, PostgreSQL et Bootstrap.

- `/` : redirection vers l’accès aux quatre parcours fictifs (`/access/`).
- `/admin/` : administration native Django (utilisateurs et groupes).
- Les modèles et migrations `journeys` sont ceux du prototype d’origine.
- Aucun email réel ni enregistrement AGLAE n’est activé en démonstration partagée.

## Démonstration partagée — adaptation du 23 octobre 2026

Les points d’entrée racine `manage.py` et `config.wsgi:application` utilisent le
prototype et les variables `DJANGO_*` / `PG*` du socle. Le lanceur autonome
`match_europe/run_local.py` et sa configuration `ME_*` sont conservés.

`make help` décrit l’installation, le serveur local, SQL et les tests.
Après configuration de `.env` et création de sa base locale :
`make install-test`, `make migrate`, `make seed-demo`, `make run`.
`make test` vérifie le point d’entrée racine ; `make test-local` vérifie aussi
la configuration autonome. `make serve` permet un essai Gunicorn sur loopback.

Le point d’entrée racine est exclusivement une démonstration. En HTTPS
(`DJANGO_HTTPS=1`), le mode partagé est activé par défaut ; `ME_SHARED_DEMO=0`
permet de le désactiver. Ce mode exige HTTPS pour les pages/API employeur,
conserve CSRF et les brouillons par session, et affiche un avertissement FR/EN/DE.
Il ne lit aucune clé AGLAE et refuse les enregistrements externes ; le diagnostic
Push reste inaccessible. La lecture de sources publiques et le géocodage peuvent
faire des requêtes réseau, comme dans le prototype local, après les actions prévues
dans l’interface. Utiliser exclusivement des données fictives.

Exécuter les migrations et collecter les statiques avant le serveur WSGI. Celui-ci
crée les quatre rôles fictifs au premier démarrage si l’identité admin fictive
n’existe pas. Il ne réinitialise pas les comptes ni les modifications aux
redémarrages suivants. PostgreSQL conserve ces données ; les fichiers déposés
dans le système de fichiers de l’instance n’ont pas de garantie de persistance.
Les journaux d’accès Gunicorn omettent les chemins et paramètres des liens privés.

Le déploiement de cette branche et sa sonde `/health/` sont préparés pour la revue ;
les procédures propres à un hébergeur et ses secrets restent dans le dépôt privé.
L’enregistrement final d’un import AGLAE reste indisponible dans ce mode :
l’interface doit afficher l’erreur et conserver le brouillon, sans annoncer un
envoi réussi. Cette adaptation n’autorise aucune utilisation en production.

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
---

# Match Europe — premier prototype Django

Archive de travail partagée pour conserver et discuter le premier prototype local Match Europe. **Cette branche et sa PR ne sont pas une proposition de mise en production ou de fusion en l’état.**

La pile est Django / PostgreSQL / Bootstrap. Le code historique Flask/Grist reste dans [eures-beta/eures-beta](https://github.com/eures-beta/eures-beta) ; il n’est pas importé comme application dans ce dépôt.

## Ce qui est conservé

- Parcours candidat, employeur, conseiller et administrateur avec données de démonstration fictives.
- Accès par lien de confirmation simulé, contrôle des droits par objet et conversation candidat–employeur–conseiller.
- Import employeur depuis PDF, URL publique ou texte, brouillons par session, vérification et contact entreprise.
- Affectation d’un conseiller aux imports par l’administration, séparée du matching de démonstration.
- Pages employeur FR/EN/DE ; **la V2 est la référence UX retenue**.
- Diagnostic Web Push local isolé, sans inscription automatique au pilote.

## Lancer en local

Prérequis : Python 3.12+, PostgreSQL et ses outils (`initdb`, `pg_ctl`, `createdb`), gettext (`msgfmt`). Le lanceur trouve aussi les binaires PostgreSQL installés avec Homebrew. Ne pas utiliser une base contenant des données réelles.

```sh
cd match_europe
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run_local.py
```

Ouvrir <http://127.0.0.1:8014/access/> pour les quatre rôles fictifs.

Pour le parcours employeur V2, arrêter le serveur HTTP précédent puis lancer :

```sh
ME_EMPLOYER_LOCAL_API=1 ME_LOCAL_PORT=8015 .venv/bin/python run_local.py
```

Ouvrir <http://127.0.0.1:8015/previews/employer-landing/import-v2-fr.html> (EN/DE disponibles). La page d’accueil employeur est `/previews/employer-landing/fr.html`.

**Attention :** ce second mode peut consulter la source publique fournie et interroger Nominatim pour un lieu. Si une clé sandbox est explicitement configurée, il peut enregistrer puis relire une offre inactive chez le prestataire. Il ne lance pas de matching, de qualification, de contact candidat ou de SMS. Sans clé, l’échec est explicite et le brouillon reste local. Les champs contact ne sont pas envoyés au prestataire ; le texte libre de l’annonce n’est pas expurgé automatiquement.

Le mode non-démo reste volontairement bloqué. Ne pas exposer ce serveur sur Internet. Les comptes démo partagés ne conviennent pas à des données personnelles réelles.

## Structure

| Chemin | Contenu |
| --- | --- |
| `match_europe/config/` | Réglages Django et journalisation |
| `match_europe/journeys/` | Modèles, migrations, droits, services, vues et tests |
| `match_europe/templates/`, `static/`, `locale/` | Templates, Bootstrap embarqué, ressources et traductions |
| `previews/employer-landing/` | Parcours employeur de référence V2, V1 conservée et diagnostic Push |
| `forms/eures-beta/` | Deux ressources de présentation héritées, pas un serveur Flask |
| `docs/` | Périmètre, décisions, ordre de lecture et limites |

## Vérifier

Depuis `match_europe/`, après initialisation de la base locale :

```sh
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py test journeys --noinput
```

Les tests PostgreSQL créent une base distincte et simulent les services externes. Aucun secret, base, session, document utilisateur ou abonnement de notification n’est versionné. Le lanceur compile les catalogues gettext ; les `.mo` sont aussi inclus comme ressources du prototype.

## Limites et lecture de la PR

Voir [le guide de revue](docs/PROTOTYPE_REVIEW.md), [l’état de reprise](HANDOFF.md), [les décisions](docs/DECISIONS.md) et [les consignes](AGENTS.md).

Ce partage conserve des étapes successives et du code exploratoire : styles en ligne, HTML généré dupliqué, prévisualisations non entièrement intégrées à Django templates, diagnostic Push surtout francophone et documentation historique. Il ne certifie ni conformité juridique, ni accessibilité complète, ni aptitude à la production. Aucun email réel n’est envoyé ; le diagnostic Push n’est pas raccordé au parcours métier.

## Web Push facultatif pour le diagnostic local

```sh
cd match_europe
.venv/bin/python -m pip install -r requirements-push-test.txt
ME_EMPLOYER_LOCAL_API=1 ME_LOCAL_PORT=8015 .venv/bin/python run_local.py
```

Ouvrir `/previews/employer-landing/push-test.html`. L’activation nécessite une action explicite et l’autorisation du navigateur. Le test envoie uniquement un message générique ; les clés VAPID générées sont ignorées dans `.runtime/`. L’abonnement est propre à la session locale. Ne pas considérer HTTP 201 ou la permission comme preuve de réception : l’utilisateur doit confirmer la bannière ou le Centre de notifications.
