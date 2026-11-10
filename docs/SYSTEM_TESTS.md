# Parcours HTTP sous 256 Mio

`make e2e-test` lance un vrai serveur Gunicorn Linux : un worker, huit threads,
256 Mio pour **tout le conteneur web**, swap désactivé et un CPU. Docker doit être
démarré. Python 3 et Git suffisent sur l'hôte ; les dépendances applicatives sont
installées dans l'image officielle Python 3.14 épinglée par empreinte.

Le serveur utilise PostgreSQL, HTTPS, les cookies, le CSRF, les migrations et les
catalogues JSON complets du dépôt. Le pilote HTTP et PostgreSQL ont leurs propres
conteneurs : leur mémoire n'est pas imputée au budget du serveur. Chaque exécution
dispose d'un réseau interne et de ressources distinctes, supprimées en fin de test.
Aucun port n'est publié sur l'hôte, aucun secret personnel n'est transmis.

## Parcours couverts

- Huit recherches métiers simultanées à froid (une par thread), puis recherche dans les vrais
  catalogues en français, anglais et allemand. Comparaison des réponses, refus
  d'un POST sans CSRF, détection des workers tués ou redémarrés.
- Pages publiques d'accueil, candidat et employeur dans les trois langues.
- Connexion employeur par email et confirmation POST ; extraction d'un vrai PDF
  fictif, structuration par le client HTTP Albert, sauvegarde de l'offre et
  présence dans le tableau de bord et la liste des offres.
- Connexion conseiller, invitation d'un employeur, confirmation puis tableau de
  bord ; cet autre employeur ne peut pas lire l'offre du premier.
- Questionnaire candidat en quatre étapes, email, confirmation POST et accès au
  profil enregistré.

Albert est un serveur HTTPS de test sur le réseau isolé, à la frontière du service
externe. Le vrai client, l'authentification, le JSON envoyé, le décodage et la
validation des preuves sont exécutés. Un repli d'extraction fait échouer le test.
Le certificat éphémère est explicitement approuvé ; TLS n'est pas désactivé.
Les emails passent par le backend Django vers des fichiers temporaires : les
liens sont suivis sans les publier. Aucun appel Albert ni email réel n'est émis.

Ce sont des tests bout en bout **HTTP**, pas un navigateur exécutant le JavaScript.
Ils ne couvrent pas tous les écrans, l'OCR, les sites externes d'offres, tous les
cas métier ni toutes les combinaisons de charge. Le plafond mémoire est un
garde-fou réel, pas une garantie générale de capacité.

## Vérifier le détecteur lui-même

`make e2e-regression` exporte l'arbre Git complet du commit
`464b68f0707d2d238dbf92450f1c062f3f4a2093`, avant le correctif mémoire #177,
et y ajoute seulement le banc de test. Aucun ancien chargeur ni catalogue n'est
modifié. Il faut disposer de ce commit localement (checkout CI complet).

Le serveur historique doit démarrer et recevoir les mêmes huit recherches
ordinaires à froid. La commande ne réussit que si les requêtes échouent **et**
que le cgroup constate une mise à mort pour manque de mémoire pendant cette
phase. Un échec de build, de migration ou de démarrage ne valide pas ce témoin.
Le rapport interne du parcours reste rouge ; le témoin négatif est alors vert.

Mesures locales Docker Linux/arm64 du 10 novembre 2026 : ancien code, plafond
268 435 456 octets atteint, `oom_kill=1`, SIGKILL et redémarrage du worker ; code
corrigé, cinq parcours réussis, pic 165 363 712 octets (157,7 Mio), aucun OOM ni
redémarrage. Une requête isolée sur l'ancien code n'a pas reproduit le défaut
dans ce banc. Quatre requêtes suffisent sur arm64, mais atteignent seulement
240 Mio sur le premier essai CI amd64. La suite utilise donc les huit threads
du serveur, sans remplissage artificiel de mémoire. La CI Linux/amd64 vérifie
la même condition indépendamment.

## CI et diagnostics

Le job « Parcours HTTP — 256 Mio » appartient au workflow de vérification de main
avant déploiement. Il tourne sur les PR et les changements de main : le workflow
ne réussit que si les tests PostgreSQL et ces parcours passent. Le témoin ancien
est également exécuté pour vérifier que le détecteur reste sensible au défaut.

Les rapports `.runtime/e2e-report.json` et `.runtime/e2e-legacy-report.json`
contiennent phases, durées, compteurs OOM et pic du cgroup. Seuls ces rapports
sont archivés par la CI, jamais les emails, cookies, liens magiques, certificats
ou clés éphémères. La suite ne remplace pas les tests unitaires et de migrations.
