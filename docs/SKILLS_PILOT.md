## Mise à jour — 9 novembre 2026

Le parcours de sélection est actif par défaut et accessible en local, recette et production. Les choix restent privés à la session, avec expiration, validation serveur et CSRF ; ils ne créent pas directement une offre ou un profil. Les anciennes restrictions local/loopback/e-mails décrites ci-dessous sont remplacées par cette décision.

# Sélection de compétences — catalogue local de 50 métiers

## Extension proposée le 6 novembre 2026

À la demande d’Eric, préparation locale de 50 métiers ESCO distincts : les six
fiches initiales et la variante nettoyage de locaux sont conservées, avec 43
ajouts. La liste et les huit compétences par métier sont des propositions
éditoriales, pas un classement statistique des besoins de recrutement.
Voir [la liste officielle et les identifiants](SKILLS_CATALOGUE_50.md).

Les deux JSON gardent leur schéma : 49 éléments dans `cards`, plus
`cleaningAlternative`, soit 50 métiers distincts. Aucun troisième catalogue,
correspondance ROME, score, salaire ou statistique d’offres n’est ajouté.
Les nouveaux intitulés affichés proviennent des libellés officiels ESCO FR/EN/DE ;
les intitulés de présentation historiques des sept choix initiaux sont conservés.

Les archives ESCO 1.2.1 locales sont contrôlées contre les empreintes épinglées
dans la PR #154. `make skills-pilot-audit CATALOG_SOURCES=/chemin/archives`
compare tous les concepts, libellés, descriptions, synonymes, types, collections
transversales et relations aux trois archives. Il vérifie 50 URI métier distinctes,
400 propositions de compétences clés et 200 propositions de savoir-être.
Chaque compétence clé a un lien officiel ; 198 associations de savoir-être sont
explicitement éditoriales et deux ont un lien officiel. Leur présence dans ESCO
ne transforme pas leur sélection éditoriale en recommandation officielle.

La reconstruction existante en staging conserve les deux fichiers à l’identique.
Le cache du catalogue reste en mémoire par processus : redémarrer les processus
après remplacement des JSON. Aucun appel Albert ou réseau à l’utilisation,
aucune migration ni collecte durable ajoutés. Le pilote garde ses protections
locales et ne raccorde pas ces choix aux offres, profils ou matching.

Le parcours automatisé couvre chaque métier pour les deux rôles en FR/EN/DE,
avec vérification des libellés, des sélections et du récapitulatif. La sélection
éditoriale reste à relire par Eric ; pas de recette navigateur supplémentaire
revendiquée pour ce lot. Aucun push, fusion ou déploiement.

## Recette initiale et fonctionnement conservé

Le pilote se teste dans l’application Django, à `/skills-pilot/?lang=fr`.
Il prépare une sélection explicite commune aux employeurs et candidats avant
intégration dans les questionnaires métier. Il ne remplace pas leurs formulaires
actuels et ne sauvegarde aucun profil ou offre.

## Démarrage

Utiliser un `.venv` et une base PostgreSQL de développement propres au worktree,
selon les commandes habituelles `make install-test`, `make db-create` et
`make migrate`. Puis lancer `make skills-pilot-run` et ouvrir
<http://127.0.0.1:9038/skills-pilot/?lang=fr>.

Le lancement active explicitement le pilote, désactive les e-mails réels et Albert,
et reste sur loopback en environnement `local`. Les vues retournent 404 sans
activation, en preview/production, si les e-mails réels sont actifs ou pour une
adresse distante non loopback. Il ne s’agit pas d’un accès employeur/candidat
authentifié : ce sont deux rôles de simulation sans données métier réelles.
Les cookies propres à cette recette évitent d’écraser les sessions d’autres ports
localhost. Ne jamais utiliser de données personnelles dans ce pilote.

## Parcours

1. Choisir employeur ou candidat.
2. Choisir l’un des 50 métiers ; le nettoyage distingue domicile et locaux.
3. Choisir au plus cinq compétences parmi huit et trois savoir-être parmi quatre.
   Aucun choix n’est imposé ou présélectionné. Champ « Autre » facultatif,
   limité à 300 caractères, sans rapprochement automatique avec un concept.
4. Relire et modifier. Les sélections sont indépendantes entre rôles et sessions.
   Un changement de métier efface uniquement la sélection du rôle courant.
   Le changement de langue conserve aussi les choix en cours par POST protégé.

Chaque brouillon expire après 30 minutes sans enregistrement. Les données restent
dans une session Django locale et ne sont pas un profil durable. L’expiration ne
constitue pas une purge physique instantanée des tables de sessions : leur
entretien reste celui de Django. Aucun e-mail, compte, offre, matching ni score.

## Données

`occupations/data/skills_pilot_sources.json` contient les concepts officiels ESCO
1.2.1 utilisés et leurs libellés FR/EN/DE, descriptions, sources, empreintes et
relations métier–compétence. `skills_pilot.json` contient la sélection éditoriale,
son ordre et les rubriques. Le chargement ne dépend d’aucun réseau.

Les huit compétences clés de chaque fiche ont une relation officielle ESCO avec
le métier correspondant. Les concepts utilisés comme savoir-être sont officiels,
mais leur proposition pour un métier est souvent éditoriale ; l’origine et la
présence éventuelle d’un lien officiel sont conservées. « Essential » dans ESCO
ne veut pas dire « obligatoire dans toute offre ». La rubrique savoir-être est
une présentation du pilote, pas une nouvelle classification officielle.

Reconstruction reproductible : `make skills-pilot-build`, avec
`CATALOG_SOURCES` pointant vers les trois archives CSV officielles ESCO 1.2.1.
Les empreintes doivent correspondre à celles épinglées dans les données.
La commande écrit uniquement `.runtime/skills-pilot-staging` : comparer ces deux
fichiers aux fichiers versionnés avant toute promotion. Une nouvelle édition,
une modification du périmètre ou une réécriture des libellés demande une revue.

Cette application utilise la classification ESCO de la Commission européenne.
Les choix éditoriaux sont propres au pilote Match Europe. Voir les
[archives officielles](https://esco.ec.europa.eu/en/use-esco/download) et les
[conditions de réutilisation](https://esco.ec.europa.eu/en/about-esco/faq?page=1).

## Vérifications

- `make skills-pilot-test` : plafonds serveur, URI admises, CSRF, expiration,
  séparation des rôles, modification, langues, échappement et absence de création
  d’utilisateurs/profils/offres.
- `make test` : suite PostgreSQL complète, avec les données fictives existantes.
- `make check`, `make format-check`, `make format-html-check`,
  `make format-js-check`, `make check-js`, `make translations-check`.

Recette navigateur : vérifier plafond atteint puis désélection, récapitulatif,
retour à la modification, conservation FR/EN/DE, changement de métier et séparation
des rôles. Tester au clavier et sur petit écran. Eric a validé le parcours local à un métier et autorisé sa publication en PR
le 6 novembre 2026. Le multi-métiers candidat reste hors périmètre. Aucune
fusion ni aucun déploiement.


## Retrait du parcours autonome — 9 novembre 2026

Après intégration aux formulaires candidat et employeur (#158), les routes
`/skills-pilot/` et leurs écrans sont supprimés. Les catalogues, leurs outils
de maintenance et le service de suggestions restent utilisés par les vrais
parcours. Aucun modèle, migration ou réponse durable n’est supprimé. Les
anciens brouillons de session ne sont plus lus ; aucune purge SQL ajoutée.
