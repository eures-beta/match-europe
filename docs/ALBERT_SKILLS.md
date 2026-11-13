## Mise à jour — 9 novembre 2026

La préparation des compétences fonctionne dans tous les environnements et est active par défaut lorsque la clé Albert est configurée. Les sources ESCO officielles vérifiées restent nécessaires. La simulation est désactivée par défaut et ne dépend pas du nom de l’environnement ; son cache reste séparé. Les anciennes exclusions local/loopback/e-mails ci-dessous sont remplacées.

# Compétences des métiers hors sélection — essai local

## Autorisation et limites

Après l’audit en lecture seule du sommet #156 (`f007a7f`), Eric autorise le lot
local proposé, désactivé par défaut et testé sans appel Albert réel. Branche
`codex/albert-occupation-skills`, empilée sur ce sommet vérifié sur GitHub.
Les deux rôles du pilote `/skills-pilot/` partagent les suggestions de référence,
mais leurs déclarations restent distinctes et temporaires. Aucun raccordement
aux offres ou profils réels, aucune publication, fusion ou production.

## Chaîne implémentée

Recherche locale dans les métiers ESCO, exclusion des 50 fiches déjà préparées,
puis confirmation explicite du métier. POST protégé vers le parcours du rôle,
avec `action=resolve` et l’URI officielle `occupation`. Aucun appel sur GET.
Le navigateur affiche avant soumission : « Un instant, nous recherchons les
compétences associées à ce métier afin de vous les proposer ». Sans JavaScript,
la soumission et les validations fonctionnent, mais ce message intermédiaire
ne peut pas être affiché avant la réponse.

Le serveur utilise uniquement les relations métier–compétence des archives
officielles ESCO 1.2.1 FR/EN/DE, vérifiées avec les trois empreintes déjà épinglées.
Albert reçoit l’intitulé officiel du métier et ses compétences reliées, pas les
réponses personnelles, le texte libre, une offre ou un profil. Il choisit 1 à 8
URI dans cette liste. Toute URI inconnue, hors métier, doublonnée, liste vide ou
sortie mal formée est refusée. Les libellés affichés viennent des sources
officielles dans la langue de l’utilisateur, jamais du modèle.

Cette règle est plus restrictive qu’une génération libre suivie d’une recherche
par ressemblance : aucune nouvelle association métier–compétence n’est créée.
Elle limite les propositions aux relations disponibles dans ESCO. Un métier
absent d’ESCO demande une reformulation ; aucun code ou rapprochement ROME
n’est inventé. La pertinence de la sélection reste à valider humainement.
Les métiers ajoutés ne reçoivent pas de savoir-être déduit automatiquement.

## Persistance et concurrence

Migration additive `occupations.0001_initial` : table partagée
`OccupationSkillSuggestion`, avec URI métier, édition/empreintes ESCO, méthode
de sélection/version de consigne/modèle, URI retenues, statut et date.
Contrainte unique sur métier + source + méthode. Les données simulées sont
séparées des données Albert réelles. Aucun texte brut de réponse ni secret
n’est stocké. Administration explicitement enregistrée en lecture seule.

Une réservation de 60 secondes empêche les doubles appels sur la même clé.
La transaction est terminée avant l’appel externe ; un identifiant de réservation
empêche une ancienne réponse de remplacer une nouvelle tentative. Les échecs
restent réessayables après une minute, sans effacer le brouillon précédent.
Les succès sont réutilisés entre rôles, sessions et redémarrages ; les URI sont
revérifiées contre les sources à la lecture. Pas de purge planifiée : il s’agit
de références publiques versionnées, pas de données personnelles. Remplacer les
archives demande une revue de version et un redémarrage du chargeur mémoire.

## Protections et recette

`SKILLS_ALBERT_ENABLED=0` par défaut. Le service exige le pilote activé,
`DJANGO_ENVIRONMENT=local` et les e-mails réels désactivés ; les vues exigent
en plus une adresse loopback réelle, sans croire `X-Forwarded-For`. Les rôles
acceptés restent `employer` et `candidate`. Même CSRF, expiration et plafonds
de sélection que le pilote existant. Les suggestions ne sont jamais précochées.

`SKILLS_ALBERT_SIMULATED=1` par défaut. Le chemin réel existe côté serveur,
avec la clé Albert existante, délai réseau de 35 secondes, refus des redirections,
limites de requête/réponse et absence de relance automatique. Aucun appel réel
n’a été effectué pour ce lot ; coût, qualité et délai réels restent non mesurés.
Une activation réelle devra être explicitement validée avant toute consommation.

Préparer un environnement et une base PostgreSQL propres au lot avec
`make install-test`, `make install-quality`, `make install-js`, `make db-create`
et `make migrate`. Placer les trois archives épinglées `esco-1.2.1-fr.zip`,
`esco-1.2.1-en.zip`, `esco-1.2.1-de.zip` dans `.runtime/catalog-sources/`.
Cette étape ne télécharge rien automatiquement. `make skills-source-check`
vérifie les empreintes et la complétude trilingue.

`make run PORT=9039` démarre le serveur sur loopback au port 9039. Pour
cet essai simulé, définir explicitement `SKILLS_ALBERT_SIMULATED=1`,
`EMAIL_DELIVERY_ENABLED=0` et `LOGIN_EMAIL_ENABLED=0` dans le `.env` du worktree.
Le démarrage ne force aucun réglage. Choisir un rôle, rechercher par
exemple « photographe », confirmer le métier, préparer les propositions,
sélectionner jusqu’à cinq compétences et relire. Tester les trois langues,
la modification, le changement de métier et le second rôle. La simulation
prend les huit premières URI triées : elle valide le parcours et le cache,
pas la qualité d’une sélection Albert.

Vérifications : `make test TESTS=tests.skills.test_albert_skills`, `make test-js`,
`make test TESTS=tests.skills.test_skills_pilot`, `make test`, `make check`, `make format-check`,
`make format-html-check`, `make format-js-check`, `make check-js`,
`make translations-check` et `make translations-compile`.

La prochaine validation produit concerne le parcours local simulé. L’évaluation
réelle d’Albert, le raccordement aux questionnaires durables et une éventuelle
publication sont des étapes distinctes. Aucun audit WCAG complet revendiqué.

## Résultats locaux

491 tests PostgreSQL réussis, dont 12 dédiés aux suggestions ; après le dernier
contrôle des textes et de l’administration, les 12 tests dédiés et les 8 tests
de lecture seule administrative ont été revérifiés avec succès. Le test
JavaScript d’attente/double soumission/retour navigateur passe. Contrôles
Django/migrations, format Python/templates/JavaScript, syntaxe JavaScript et
traductions FR/DE compilées réussis. Installation et migration sur base vide.
Archives officielles locales contrôlées : 13 939 concepts et 3 039 métiers avec
relations. Les fichiers d’archives restent hors Git.

Recette navigateur sur « photographe » hors des 50 fiches : préparation simulée,
choix explicite employeur conservé en FR→EN→DE→FR, récapitulatif, second rôle
candidat avec mêmes suggestions et choix indépendants. Confirmation au clavier
et message d’attente observés. À 390 pixels : largeur du document et largeur
visible égales, sans débordement horizontal. Ressources de marque existantes
conservées ; aucun audit complet WCAG ou lecteur d’écran revendiqué.
Aucun appel Albert réel, envoi d’e-mail, push, PR, fusion ou déploiement.
