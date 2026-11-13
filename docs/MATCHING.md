# Matching : correspondances explicables

## Périmètre et accès

Le matching compare les profils candidats confirmés et les offres validées.
Il fonctionne en développement, recette et production, avec les comptes actifs
réels ou fictifs autorisés. `MATCHING_ENABLED` est actif par défaut ; la valeur
`0` désactive la fonctionnalité. Il n'existe pas de restriction métier liée à
l'environnement, à l'adresse réseau ou à l'activation des e-mails.

La console `/matching/` est accessible à tout conseiller connecté et actif,
en consultation comme pour les actions POST, sans permission Django supplémentaire.
Tous les conseillers ont les mêmes droits métier.
Le calcul ne modifie ni l'offre ni le profil. Il n'envoie pas de message, de
notification, d'appel Albert ou d'autorisation de transmission.

## Décisions métier validées dans cette conversation

- Une information absente ou non sélectionnée reste inconnue, pas incompatible.
- Une exclusion de paire exige une incompatibilité explicite et une exigence
  non négociable. Premier périmètre : horaires stricts, date limite impérative,
  autorisation indispensable explicitement non détenue à la date requise.
- Les autres écarts restent soumis à examen humain. Aucune exclusion au score.
- Le métier souhaité est visible, hors score initial. Les compétences déclarées
  ne sont jamais inférées d’un métier. Aucune équivalence ESCO/ROME automatique.
- Apprentissage séparé des acquis ; savoir-être sans points ni exclusion.
- Recalcul et décision humaine sont distincts. Un recalcul conserve le refus.
- Cible conversationnelle ultérieure : Albert revient vers le candidat sur
  une correspondance possible pour confirmer les points saillants. Une réponse
  contradictoire exige de préciser « cette offre » ou « de manière générale ».
  Une exception propre à l’offre ne remplace pas le profil. Silence et accord
  de transmission restent distincts. Aucun de ces dialogues n’est implémenté ici.

## Calcul et limites explicites

`matching/engine.py` est une fonction déterministe sans ORM ni réseau. Les
états sont `match`, `mismatch`, `unknown`, `not_applicable`. Chaque élément
porte un motif stable, une dimension et un éventuel blocage. Les codes de
questions des inconnus sont disponibles pour le futur dialogue, sans envoi.
Les explications FR/EN/DE sont produites séparément dans `presentation.py`.

**Hypothèse de laboratoire, pas pondération validée** : compétences 40,
langues 20, pays souhaité 15, disponibilité/conditions 15, salaire 10.
Métier et savoir-être : zéro. Dans une dimension, le budget est partagé à
parts égales entre les éléments évalués. Ce choix reste à calibrer et versionner.
L’écran affiche les points établis et le budget inconnu, jamais un pourcentage
de réussite, un classement ou un seuil de rejet. Les absences n’apportent pas
de points et ne sont pas des preuves négatives. Les exigences explicitement
absentes n’apportent pas de bonus ; leur budget n’est pas redistribué.
La couverture donne des nombres d’exigences évaluables par dimension, pas une
probabilité ni une certification de la personne. Le score ne décide d’aucun envoi.

`review` signifie au moins une correspondance établie sans blocage confirmé.
Il s’agit d’un état pour l’opérateur, **pas d’un critère validé de sollicitation
candidat**. Aucun fait favorable donne `insufficient` ; un blocage donne `blocked`.
Ces états ne prouvent pas que toutes les exigences sont satisfaites.

Adaptation aux données existantes :

- `CandidateProfile.acquired_skills` et `occupation_skills` : seules les URI
  explicitement déclarées sont utilisées. Compétences employeur dans
  `JobOffer.data.occupationSkills`. Plusieurs métiers employeur restent à
  clarifier : leurs exigences ne sont pas fusionnées en obligations conjointes.
- Les niveaux linguistiques sont comparés par codes ISO et niveaux CECRL
  lorsque les exigences employeur structurées existent.
- Un pays souhaité commun établit uniquement cet alignement, pas un trajet
  réalisable ou un droit au travail. Un pays non choisi n’est pas un refus.
- Les dates absolues et la réponse « maintenant » sont comparables ; « dans un
  mois » n’est pas converti sans date de déclaration fiable.
- Les créneaux employeur des exigences structurées désignent une présence requise
  dans chacun des créneaux, pas des rotations alternatives.
- Un permis absent d’une liste candidat reste inconnu. La preuve négative
  déclarée est explicitement valable à la date de prise de poste requise ;
  l’absence actuelle seule ne permettrait pas de conclure à cette absence future.
- Un écart linguistique ou salarial ne bloque pas. Le salaire n’est comparé
  que par heure, même devise et même brut/net. Les montants mensuels/annuels
  restent à vérifier faute de durée de travail commune précise. Aucun taux
  de change ni conversion de brut/net, aucun parsing libre.
- Les textes employeur sur salaire, langues, dates ou horaires restent inconnus.
  Il faut les structurer et les confirmer dans un lot suivant.

## Données et accès

Trois modèles de matching après consolidation des exigences dans l'offre :

- `CandidateOfferMatch` : paire unique candidat/offre, décision courante et faits explicitement déclarés ;
- `CandidateOfferReview`, `CandidateOfferReviewAnswer` et `CandidateProfileSharing` :
  examen de l’offre par le candidat, réponses par question et choix de partage
  distincts ; voir [les confirmations par offre](CANDIDATE_OFFER_CONFIRMATIONS.md).
- `MatchEvaluation` : résultat, version, date et empreinte des entrées ; aucune copie
  complète de profil ni coordonnées ;
- `MatchDecision` : événement de décision rattaché au calcul, daté, libellé d'opérateur explicite. Ce libellé ne remplace pas le contrôle d'accès
  du compte conseiller connecté.

Les exigences explicites appartiennent à `JobOffer.structured_requirements`,
validées dans `employers` : langues, pays, date, horaires, permis et salaire.
Aucune contrainte n'est inférée automatiquement d'un texte libre.
`employers.0006` ajoute ce champ, puis `matching.0004` copie les valeurs de
l'ancien `OfferRequirements` avant de supprimer sa table. Les offres, leurs dates,
les paires et leurs calculs restent intacts ; des valeurs contradictoires font
échouer la migration. Le retour arrière restaure les valeurs structurées dans
l'ancienne table, avec de nouveaux identifiants et dates techniques de ces lignes.
Les exigences sont aussi recopiées lors de la duplication explicite d'une offre.

La paire et les suppléments sont dans PostgreSQL. Les décisions ne sont pas
écrasées par le recalcul. Une décision exige la dernière évaluation et des
entrées inchangées (profil, offre, révision, suppléments, faits, règles, jour).
Les décisions sont sérialisées par verrou de paire. Les modifications concurrentes
futures des profils demanderont une stratégie de révision partagée avant production.
Le bouton « Retenir pour examen » reste indisponible si blocage, données périmées
ou aucune correspondance. Un refus peut être révisé explicitement par l’opérateur,
avec un nouvel événement. Aucun consentement ni transmission n’en découle.

Les accès sont contrôlés côté serveur ; calcul et décisions utilisent POST et
CSRF. Seuls les profils confirmés de comptes candidats actifs et les offres
validées de comptes employeurs actifs sont éligibles. Les noms et titres sont
affichés, pas les e-mails. L'administration reste limitée aux métadonnées en
lecture seule, sans suppression ou exposition des résultats et faits.

Pas de purge automatique ajoutée. Pour un usage durable,
fixer la rétention des évaluations, des confirmations et des événements. Les
suppressions de profil/offre entraînent celles des objets de matching associés.

## Installer et essayer

Un `.venv` et un `.env` propres au dossier, avec Python 3.14 et PostgreSQL.
Dépendances : `make install-test`, `make install-quality`.
Pour une instance locale séparée : `make matching-db-init`, puis
`make matching-db-start` (loopback, port 55441). Cette instance utilise le rôle
local `matching_local`, authentification de recette sans mot de passe, jamais
à exposer sur le réseau. Définir `PGHOST=127.0.0.1`, `PGPORT=55441`,
`PGUSER=matching_local` et un `PGDATABASE` propre au dossier dans `.env`.
Définir une clé Django locale, `DJANGO_DEBUG=1`, `MATCHING_ENABLED=1`,
`DJANGO_ENVIRONMENT=local`, `EMAIL_DELIVERY_ENABLED=0`, `LOGIN_EMAIL_ENABLED=0`.

Puis `make db-create`, `make migrate`, `make matching-translations`,
`make run PORT=9041`.
Ouvrir http://127.0.0.1:9041/matching/ avec un compte conseiller actif.
Pour des scénarios fictifs dans une base de développement ou de recette dédiée,
activer explicitement `TEST_ACCOUNTS_ENABLED=1`, garder les e-mails désactivés,
puis utiliser `make matching-seed`. Ce peuplement est distinct de l'accès métier.
Choisir ensuite une paire ou un scénario.
Le peuplement ne remplace pas les réponses ni les décisions existantes.
Scénarios : correspondances favorables, inconnus/apprentissage, date bloquante,
horaires bloquants, autorisation explicitement absente à la date requise.
Chaque profil et offre est un objet des applications actuelles, pas un calcul
sur une copie statique. Les scénarios conservent leur date de création ; recréer
une base jetable pour des exemples datés plus tard.

Arrêter le serveur avec Ctrl-C et la base dédiée avec `make matching-db-stop`.
Ne pas modifier ou arrêter les autres instances PostgreSQL de la machine.

## Vérification

- `make test TESTS=eures_beta.matching` : logique, inconnus, trois blocages, langues/salaire,
  choix métier hors score, conservation des décisions, conflits, accès et langues.
- `make test` : suite complète PostgreSQL des domaines actuels.
- `make check`, `make translations-check`, `make format-check`,
  `make format-html-check` : cohérence et formatage.

La validation métier des poids, une recette métier étendue et l’audit complet
d’accessibilité restent distincts de ces contrôles techniques.

## Présentation des résultats

La liste affiche le score sur 100, l'état du calcul et la décision humaine,
puis les sous-scores et explications au dépliage. La fiche distingue points
forts, incompatibilités explicites et points à confirmer. Une évaluation périmée
reste signalée. La consultation n'enregistre ni calcul ni décision.
Les poids restent expérimentaux, sans seuil automatique de rejet.
