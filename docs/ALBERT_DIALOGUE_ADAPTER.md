## Mise à jour — 9 novembre 2026

Le dialogue Albert fonctionne dans tous les environnements, avec une clé privée configurée ; il est actif par défaut. La simulation est explicitement choisie pour les essais, jamais imposée par l’environnement. Les appels envoient uniquement la condition de l’offre, les déclarations correspondantes, les paroles et l’historique utile du dialogue ; aucune transmission automatique à l’employeur ni modification de profil sans relecture explicite. La CSRF, la vérification de la propriété de la demande, les quotas et les contrôles de version sont conservés. Sans clé ou en cas d’échec, le formulaire guidé reste disponible. Les anciennes restrictions locales ci-dessous sont remplacées.

# Raccordement du dialogue à Albert — recette fictive uniquement

## Périmètre et état

Eric autorise le raccordement du dialogue du site avant la PWA et les
notifications. Ce lot prolonge le prototype local `d03c2a9` issu de #162
(`20df0b7`). La simulation reste disponible. La production et la transmission
employeur restent fermées. Aucun appel réel n’est exécuté par les tests automatisés.

Le connecteur suit l’API Chat Completions documentée par Albert :
https://albert.api.etalab.gouv.fr/reference. Il utilise le mode JSON, sans outils,
streaming ni exécution de code. La disponibilité du modèle configuré et la qualité
de ses réponses devront être vérifiées par l’évaluation réelle avant activation.

## Dialogue et validation

- Une condition à la fois, à partir des conditions structurées de l’offre et des
  déclarations du candidat directement liées à cette condition.
- Réponse libre, éventuelles questions de précision, reformulation, puis POST
  explicite du candidat pour enregistrer. Les messages du modèle sont échappés ;
  les liens et balises dans une réponse modèle sont refusés.
- Réserve propre à l’offre et changement général séparés. Le choix explicite de
  portée du candidat ne peut pas être contredit par le modèle.
- Les propositions de profil sont limitées aux champs de la condition courante,
  validées par les champs Django et accompagnées d’extraits exacts des paroles
  du candidat. La preuve textuelle ne garantit pas l’interprétation sémantique :
  la relecture humaine avant/après et la validation restent indispensables.
- Horaires, disponibilité, contrat, salaire, mobilité, permis et conditions de
  travail disposent d’un sous-ensemble de champs autorisés. Aucune compétence,
  certification, référence ESCO/ROME ou identité ne peut être attribuée par le
  modèle. Les autres modifications passent par le formulaire habituel.
- Une modification de profil est d’abord un brouillon ; les formulaires complets
  et leur contrôle de cohérence restent obligatoires avant l’écriture durable.
  La version de profil initiale est revérifiée sous verrou au dernier POST.
- L’accord de transmission reste séparé, dans le parcours existant. Aucun appel
  Albert n’est effectué pendant la transaction de validation, aucun score n’est
  changé et aucun profil n’est transmis à un employeur.

## Données et limites

L’envoi contient la langue, la condition, les déclarations associées, les champs
de modification autorisés et les seuls échanges de cette condition. Le connecteur
ne reçoit pas le profil complet, le nom, l’email, l’identifiant du candidat ou les
coordonnées employeur. Un candidat peut toutefois saisir des données sensibles
dans son texte libre : ne tester qu’avec des données fictives ; le filtrage et les
conditions d’usage pour des données réelles restent à définir.

Historique de clarification signé et limité à quinze minutes, lié au candidat,
à la demande, à la condition et au contexte. Au maximum six messages historiques,
2000 caractères cumulés de paroles candidat ; au-delà, retour au formulaire.
Pas de conversation entière durable côté serveur ; après validation, les paroles
ayant fondé la réponse sont dans l’événement existant de confirmation. Les règles
de conservation et de purge avant usage réel restent ouvertes.

Six tentatives réseau maximum par candidat sur quinze minutes, compteur atomique
dans la table de limites existante avec clé hachée dédiée. Délai réseau de
25 secondes, réponse limitée à 20 ko et 1800 tokens, aucune relance automatique,
aucune redirection HTTP. Une réponse tronquée, invalide ou hors schéma ferme le
traitement et propose le formulaire guidé sans écriture métier.

## Configuration et vérifications

Le connecteur est disponible avec un accès Albert configuré ;
`ALBERT_SIMULATED=1` reste prioritaire et empêche l’appel réel.
La simulation est désactivée par défaut. Les gardes locales, fictives et par
propriétaire de #162 restent obligatoires, même avec une clé configurée.
`ALBERT_DIALOGUE_MODEL` permet de choisir le modèle ; son défaut est `ALBERT_MODEL`.
Le secret est fourni uniquement par la configuration protégée de l’environnement.

- `make test TESTS=tests.matching.test_dialogue_albert` : tests du connecteur avec réponses API mockées.
- `make test TESTS=tests.matching.test_dialogue` : tests du simulateur.
- `make run PORT=9045` : application locale sur loopback 9045 ; nécessite
  un accès configuré et
  `ALBERT_SIMULATED=0` dans le `.env` pour dialoguer réellement,
  sinon repli explicite. Le démarrage ne modifie pas ces réglages.
- `make dialogue-live-evaluate` : opt-in réel, six échanges fictifs au maximum,
  FR/EN/DE, sans base de données. Sortie limitée aux résultats, sans réponses
  brutes ni secret. Cette commande consomme le quota du service.
- `make test`, `make check`, `make format-check`, `make format-html-check`,
  `make translations-check` : vérifications habituelles. Vérifier également
  l’extraction des traductions dans une copie isolée.

Le modèle réel n’a pas encore été évalué dans ce lot. Le contrôle automatique ne
peut pas prouver une absence d’hallucination ; une campagne métier multilingue,
des essais de charge, la validation RGPD et un audit d’accessibilité complet
restent nécessaires avant toute ouverture à de vraies données.
