# Parité fonctionnelle des environnements

Décision d’Eric du 9 novembre 2026 : les fonctionnalités livrées sont destinées au local, aux recettes jetables et à la production. Leur disponibilité ne dépend ni du nom de l’environnement, ni du mode démo, ni d’une adresse loopback ou fictive, ni de la désactivation des e-mails. Cette décision remplace les anciennes restrictions de prototype dans les documents historiques.

## Corrections

- #132 : le transport commun des e-mails dépend de son activation explicite et de sa configuration, sans exclusion d’environnement. Il reste désactivé par défaut.
- #133 et #146 : profil employeur et import accessibles avec les droits du compte réel ; Albert utilisable avec une clé configurée, sans prérequis de démonstration.
- #154 et #157 : sélection de compétences accessible à distance ; génération Albert réservée au rôle authentifié correspondant, avec références ESCO vérifiées.
- #158 : compétences intégrées aux formulaires et espaces propriétaires dans tous les environnements ; aucune simulation Albert forcée. Liste et rattachement des offres utilisent la connexion commune. Les confirmations fictives dans le navigateur sont retirées ; le candidat suit le parcours d’e-mail vérifié avant saisie.
- #160 : profils vérifiés et offres validées aux adresses ordinaires éligibles, avec permissions explicites dans la console de matching. Le portefeuille d’équipe de la #161 est reporté. Aucun droit implicite par IP, rôle de superutilisateur ou adresse de contact.
- #162 et #163 : confirmations et dialogue candidat disponibles à distance ; accord de transmission distinct, relecture des modifications du profil, quotas, CSRF, révocation et détection des modifications concurrentes conservés.

Les PR intermédiaires conservent leurs fonctionnalités et reçoivent le socle corrigé. Les changements publiés en parallèle sur la pile ont été conservés, notamment les migrations candidat réorganisées et les contrôles de propriété des brouillons.

## Configuration nécessaire

Les fonctionnalités métier sont actives par défaut. Les anciennes options `ALBERT_IMPORT_ENABLED`, `SKILLS_PILOT_ENABLED`, `SKILLS_ALBERT_ENABLED`, `CONTINUOUS_SKILLS_ENABLED` et `CONFIRMATION_DIALOGUE_ENABLED` restent des commandes explicites de configuration, sans restriction par environnement. Une ancienne valeur explicite `0` reste une désactivation choisie : la retirer ou l’actualiser dans le dépôt privé de déploiement si elle n’est plus souhaitée. Le matching utilise `MATCHING_ENABLED`.

Albert nécessite une clé privée et son modèle configuré. Les simulations `ALBERT_IMPORT_SIMULATED`, `SKILLS_ALBERT_SIMULATED` et `CONFIRMATION_DIALOGUE_SIMULATED` sont désactivées par défaut et ne sont jamais activées automatiquement par le nom de l’environnement. Les replis guidés/manuels sont conservés.

Les compétences hors des fiches intégrées nécessitent les sources officielles ESCO épinglées : les préparer pendant la construction de l’environnement avec `make continuous-source-prepare`, puis les vérifier avec `make skills-source-check`. Ne pas télécharger ces archives pendant une requête utilisateur. Leur absence doit produire une indisponibilité explicite, jamais des références inventées.

Les e-mails nécessitent `EMAIL_DELIVERY_ENABLED=1`, `LOGIN_EMAIL_ENABLED=1`, une origine HTTPS de confiance et le transport SMTP configuré. Aucun identifiant ni destinataire n’est inscrit dans le dépôt. Les outils de comptes fictifs et de peuplement restent explicitement réservés aux bases d’essai, incompatibles avec l’envoi réel ; ils ne conditionnent pas le parcours métier.

## Vérifications

`make test` : 605 tests PostgreSQL réussis au sommet après intégration du client Albert partagé et actualisation de la pile distante ; suites intermédiaires complètes également vérifiées : 509 tests pour #158 et 558 pour #161. `make environment-parity-test` regroupe les contrôles de configuration et de parcours local/recette/production avec des intégrations simulées. Les tests exercent des requêtes distantes, des adresses ordinaires, les mêmes opérations métier et les refus d’accès ; les noms d’environnement sont des configurations de test, pas une vérification des services distants.

Contrôles complémentaires : Django, absence de migration oubliée, installation sur base neuve, formats Python/templates/JavaScript, syntaxe et tests JavaScript, traductions FR/DE. Aucun e-mail ni appel Albert réel pendant ces vérifications. Les secrets, sources préparées et transports des environnements distants restent à leur configuration privée ; aucune fusion, aucun déploiement ou changement de données de production n’est réalisé ici.
