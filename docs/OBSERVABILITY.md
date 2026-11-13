# Comprendre les requêtes lentes

Le paquet [observability](../eures_beta/observability/) produit des lignes JSON
sur la sortie standard, sans service externe ni requête de diagnostic en base.
L’hébergeur collecte ces lignes. Leur horodatage, instance et processus permettent
de les rapprocher des courbes CPU/mémoire de la même instance.

## Événements

- `request_started` : début d’une vue POST/PUT/PATCH/DELETE échantillonnée ;
- `request_completed` : bilan d’une requête applicative, succès ou erreur ;
- `worker_timeout` : diagnostic demandé par le hook `worker_abort` de Gunicorn.

Une requête reçoit un identifiant aléatoire créé côté serveur, retourné dans
l’en-tête `X-Request-ID`. Un identifiant fourni par le navigateur n’est pas repris.
Les noms de routes sont ceux de Django, ou le module et nom de la fonction pour
une route non nommée. Les chemins bruts et leurs paramètres ne sont jamais utilisés
comme libellés ; une requête non résolue porte le libellé `unresolved`.

Exemple fictif abrégé :

```json
{"event":"request_completed","request_id":"abc123","route":"employer_offer_edit","status":200,"duration_ms":4200,"sql_count":3,"sql_ms":18,"stages":{"geocode":{"count":1,"duration_ms":4000,"failed_count":0}}}
```

## Mesures

| Champ | Signification |
| --- | --- |
| `duration_ms` | Durée monotone depuis l’entrée dans le middleware. |
| `sql_count`, `sql_ms` | Nombre et temps cumulé des appels execute/executemany sur les connexions du thread de la requête, sans activer DEBUG ni conserver le SQL. |
| `sql_in_flight` | Nombre d’appels SQL en cours au moment du diagnostic. |
| `stages` | Compteurs, durée cumulée et nombre d’échecs des étapes instrumentées. |
| `active_stages` | Étapes non encore terminées, utiles pour les timeouts. |
| `pid`, `instance`, `release` | Processus et identifiants techniques de l’environnement, ou `unknown` s’ils ne sont pas disponibles. |
| `duration_scope` | `application` pour une réponse ordinaire ; `response_headers` pour une réponse diffusée en streaming. |

Les étapes métier sont une liste fermée : téléchargement public
(`source_download`), analyse des pages/PDF (`source_parse`), extraction de document
(`document_extract`), géocodage (`geocode`), appel AGLAE (`external_submission`)
et création de l’import (`import_save`). Elles mesurent le code existant sans
changer ses protections, délais maximaux ni traitements.
Les étapes imbriquées se recouvrent : ne pas additionner leurs durées comme si
elles étaient indépendantes. Les données retenues sont agrégées, pas une liste
de chaque requête SQL ou de chaque document.

## Volume et réglages

| Variable d’environnement | Défaut | Effet |
| --- | --- | --- |
| `REQUEST_METRICS_ENABLED` | `1` | Mettre `0` pour désactiver le middleware et les mesures par requête. |
| `REQUEST_METRICS_SAMPLE_RATE` | `1` | Proportion des requêtes ordinaires conservées, entre 0 et 1 ; par exemple `0.1` pour environ 10 %. |
| `REQUEST_METRICS_SLOW_MS` | `1000` | Seuil au-delà duquel le bilan est conservé même hors échantillon. |

Les erreurs HTTP 4xx/5xx sont également conservées hors échantillon. Les requêtes
vers `/health/` et `/static/` ne produisent pas de télémétrie applicative.
Au démarrage, chaque requête applicative réussie produit un bilan ; une requête
POST/PUT/PATCH/DELETE échantillonnée produit aussi son début. À plus fort trafic,
réduire l’échantillonnage. Le registre en mémoire ne contient que les requêtes
en cours, est nettoyé même en cas d’exception et reste propre à chaque processus.
Les étapes ont des noms fixes ; aucune accumulation de données par URL ou client.

Les identifiants de requête servent à la corrélation des logs : ne pas les utiliser
comme dimensions de métriques agrégées. La rétention, l’export et les alertes
relèvent de l’exploitation ; cette PR n’ajoute ni stockage durable ni tableau de
bord de statistiques de latence. Les lignes d’accès minimales de Gunicorn peuvent
rester visibles en plus des bilans JSON.

## Timeout et confidentialité

Gunicorn charge le hook depuis `gunicorn.conf.py`. Lors d’un abandon de worker,
il tente d’émettre les requêtes actives avec au maximum 16 requêtes et 20 frames
par pile. Les frames contiennent uniquement module, fonction et numéro de ligne :
ni variables locales, ni lignes de code source, ni messages d’exception.
Le hook n’effectue aucun appel réseau ni SQL. Il ne garantit pas un événement
si le processus est déjà tué par SIGKILL, manque de mémoire ou reste bloqué dans
un état où Python ne peut plus exécuter son gestionnaire de signal.

Les nouveaux événements n’enregistrent ni adresse IP, e-mail, compte utilisateur,
URL ou query string, cookies, en-têtes, texte SQL, paramètres SQL, contenu de PDF,
contenu d’offre ou réponse applicative. Le mode de lancement générique ne journalise
plus les chemins et IP dans ses lignes d’accès. Les autres loggers du projet
restent distincts ; ce module n’est pas un filtre universel de toute bibliothèque.

## Limites de mesure

Le temps commence quand Django reçoit la requête : il ne mesure pas l’attente
chez le proxy, dans la file de Gunicorn ni le réseau du navigateur. Pour les
réponses streaming, il s’arrête à la préparation des en-têtes, pas à la fin du
transfert. Le SQL concerne les appels du thread suivi, hors fetch des résultats,
travaux de fond et connexions ouvertes dans d’autres threads. Django adapte le
middleware synchrone sous ASGI ; ce n’est pas une instrumentation distribuée de
toutes les tâches asynchrones.

## Vérifier

Depuis la racine :

```bash
make test TESTS=eures_beta.observability
make test
make check
```

Les tests couvrent données sensibles, échantillonnage, SQL sur PostgreSQL,
nettoyage après erreur, contexte de deux requêtes concurrentes, réponse streaming,
adaptation ASGI, mesures d’un vrai parseur et configuration du hook Gunicorn.
