# Mémoire de la recherche de métiers

Le chargement à froid lisait chaque fichier JSON entier en octets, puis créait
une seconde copie Unicode avant le décodage. Les index utilisaient un ensemble
Python pour chaque libellé. La recherche ROME indépendante chargeait également
les correspondances ESCO–ROME sans les utiliser. Enfin, `lru_cache` ne garantit
pas qu'un seul thread calcule une valeur absente du cache.

Le chargeur utilise désormais `ijson` (version verrouillée) pour parser depuis
un fichier binaire, sans copies complètes octets/Unicode. Cette dépendance a une
responsabilité précise : éviter le pic de décodage JSON, sans inventer un parseur
maison. Le SHA-256 est vérifié avant décodage, sur le même descripteur ouvert.
Les valeurs JSON et les réponses métier sont conservées. Le document entier est
validé ; un fichier corrompu ne déclenche aucun téléchargement de secours.

Les index utilisent de petites listes de références uniques. Le catalogue ROME
de recherche charge seulement ROME et OGR ; le catalogue complet reste disponible
aux outils de validation. Un verrou réentrant englobe chaque accès aux caches
de construction : plusieurs premiers appels ne fabriquent plus plusieurs copies.

## Reproduction et vérification

- `make occupations-memory-benchmark` : un processus Django neuf exécute le POST
  synthétique `industrial electrician`, langue FR, contexte de maintenance
  électrique, recherche indépendante ESCO/ROME. Aucun réseau, compte ou accès
  à une base n'est nécessaire. Le pic RSS inclut le démarrage de Django.
- `make test TESTS=eures_beta.occupations.tests.test_search_memory` : budget de 145 Mio, égalité des quatre fichiers
  décodés avec le parseur standard, huit recherches simultanées avec chargement
  unique et résultats identiques.
- `make occupations-memory-serve` : serveur HTTP local sur `127.0.0.1:9048`,
  un worker et huit threads. Utilise uniquement le `.env` et la base locaux.
  L'appel POST réel doit conserver cookie et en-tête CSRF du formulaire.
- `make test check format-check` : autres garde-fous.

Mesures du 10 novembre 2026 sur macOS arm64, Python 3.14, mêmes dépendances
Django : avant, environ 167–169 Mio et 0,38–0,47 s ; après, environ 121 Mio et
0,35 s. Le POST sur Gunicorn local répond HTTP 200 en 0,37 s. La requête anglaise
dans cette langue et avec ce contexte retourne zéro proposition avant comme
après ; les recherches françaises ont leurs propres tests de résultats.

Le test mémoire doit échouer sur le commit de reproduction et passer après le
correctif. Ce budget est un garde-fou de régression pour le processus isolé,
pas une promesse de consommation globale : autres routes, allocations retenues,
threads et différences Linux/macOS comptent aussi. Aucun SIGKILL n'a été reproduit
sur le poste local. La réduction du pic est mesurée, mais la cause OOM distante
et la marge finale doivent être confirmées sur une instance à mémoire limitée.
Ne pas tester cette charge en boucle sur un service partagé.

## 13 novembre 2026 — chargement des bibliothèques Push

L’import du SDK Push depuis les routes candidat faisait monter le processus
de recherche à environ 147,7 Mio en CI Linux, au-dessus du budget de 145 Mio.
Les imports cryptographiques sont maintenant effectués uniquement lors des
opérations Push qui les utilisent. Les contrôles d’accès et le protocole restent
identiques. Sur macOS arm64, le même benchmark passe de 142,69 à 127,53 Mio ;
la mesure Linux est vérifiée séparément par la CI. Le seuil n’est pas augmenté.
