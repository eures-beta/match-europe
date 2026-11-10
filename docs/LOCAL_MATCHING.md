## Mise à jour — 9 novembre 2026

Le matching fonctionne dans tous les environnements et accepte les comptes réels actifs, les profils vérifiés et les offres validées. Le nom historique `MATCHING_LOCAL_ENABLED` est compatible ; `MATCHING_ENABLED` le remplace dans les nouvelles configurations, actif par défaut. La console autonome exige un conseiller avec le droit explicite `matching.view_matchpair`, et `matching.change_matchpair` pour écrire. Les restrictions IP, démo et e-mails sont retirées. Le peuplement fictif demeure une commande d’opérateur explicitement activée, séparée du parcours métier. Les scores, règles de décision et confirmations humaines restent inchangés. Les limites locales ci-dessous sont historiques et remplacées.

# Matching local : correspondances explicables

## Périmètre

Autorisé par Eric le 7 novembre 2026 : implémenter et démarrer localement le
matching Django avant de préparer l’outil conversationnel. Base de livraison
vérifiée sur GitHub : #159, `c39c728`, au-dessus de #158/#157/#156.
Branche locale `codex/local-explainable-matching`. Aucune fusion, publication,
recette distante ou production autorisée par cette étape.

Volet TRANSVERSE : profils candidats et offres employeur fictifs. Aucun accès
nouveau aux espaces employeurs, candidats ou conseillers. L’écran est un outil
local d’opérateur, pas le futur espace conseiller. Aucun envoi, notification,
appel Albert ou autorisation de transmission. Le calcul ne modifie ni l’offre
ni le profil. Les pages publiques restent inchangées.

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
- Les créneaux employeur du supplément local désignent une présence requise
  dans chacun des créneaux, pas des rotations alternatives.
- Un permis absent d’une liste candidat reste inconnu. La preuve négative
  locale est explicitement valable à la date de prise de poste requise ;
  l’absence actuelle seule ne permettrait pas de conclure à cette absence future.
- Un écart linguistique ou salarial ne bloque pas. Le salaire n’est comparé
  que par heure, même devise et même brut/net. Les montants mensuels/annuels
  restent à vérifier faute de durée de travail commune précise. Aucun taux
  de change ni conversion de brut/net, aucun parsing libre.
- Les textes employeur sur salaire, langues, dates ou horaires restent inconnus.
  Il faut les structurer et les confirmer dans un lot suivant.

## Données et accès locaux

Migration additive `matching.0001_initial`, quatre modèles :

- `MatchPair` : paire unique candidat/offre, décision courante et faits fictifs
  explicites de recette ;
- `MatchEvaluation` : résultat, version, date et empreinte des entrées ; aucune copie
  complète de profil ni coordonnées ;
- `Decision` : événement de décision rattaché au calcul, daté, opérateur local
  explicite ; ce n’est pas un compte conseiller ni une identité usurpée ;
- `OfferRequirements` : supplément structuré des scénarios fictifs, distinct du
  JSON d’offre habituel et sans inférence de texte. Validation des codes et types.

La paire et les suppléments sont dans PostgreSQL. Les décisions ne sont pas
écrasées par le recalcul. Une décision exige la dernière évaluation et des
entrées inchangées (profil, offre, révision, suppléments, faits, règles, jour).
Les décisions sont sérialisées par verrou de paire. Les modifications concurrentes
futures des profils demanderont une stratégie de révision partagée avant production.
Le bouton « Retenir pour examen » reste indisponible si blocage, données périmées
ou aucune correspondance. Un refus peut être révisé explicitement par l’opérateur,
avec un nouvel événement. Aucun consentement ni transmission n’en découle.

Accès fermé par défaut. `/matching-local/` exige `MATCHING_LOCAL_ENABLED=1`,
environnement `local`, aucun email activé, aucune démo partagée et connexion
loopback réelle. Les en-têtes de proxy ne permettent pas de contourner ce contrôle.
POST avec CSRF pour calcul et décisions. Seuls les profils confirmés de comptes
candidats actifs `.invalid` et les offres validées de comptes employeurs actifs
`.invalid` sont éligibles. Les noms et titres sont affichés, pas les emails.
L’opérateur local peut comparer toutes ces données fictives ; pas d’accès aux
comptes réels, pas de moteur de production. Admin limité aux métadonnées en lecture
seule, sans écriture, suppression ou exposition des résultats et faits.

Pas de purge automatique ajoutée. Utiliser une base jetable ; avant usage durable,
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
Définir une clé Django locale, `DJANGO_DEBUG=1`, `MATCHING_LOCAL_ENABLED=1`,
`DJANGO_ENVIRONMENT=local`, `EMAIL_DELIVERY_ENABLED=0`, `LOGIN_EMAIL_ENABLED=0`.

Puis `make db-create`, `make migrate`, `make matching-translations`,
`make matching-seed` et `make matching-run`.
Ouvrir http://127.0.0.1:9041/matching-local/ et choisir une paire ou un scénario.
Le peuplement ne remplace pas les réponses ni les décisions existantes.
Scénarios : correspondances favorables, inconnus/apprentissage, date bloquante,
horaires bloquants, autorisation explicitement absente à la date requise.
Chaque profil et offre est un objet des applications actuelles, pas un calcul
sur une copie statique. Les scénarios conservent leur date de création ; recréer
une base jetable pour des exemples datés plus tard.

Arrêter le serveur avec Ctrl-C et la base dédiée avec `make matching-db-stop`.
Ne pas modifier ou arrêter les autres instances PostgreSQL de la machine.

## Vérification

- `make matching-test` : logique, inconnus, trois blocages, langues/salaire,
  choix métier hors score, conservation des décisions, conflits, accès et langues.
- `make test` : suite complète PostgreSQL des domaines actuels.
- `make check`, `make translations-check`, `make format-check`,
  `make format-html-check` : cohérence et formatage.

La validation métier des poids, une recette métier étendue et l’audit complet
d’accessibilité restent distincts de ces contrôles techniques.

## 8 novembre 2026 — résultats visibles sur le modèle de Flask

À la demande d’Eric, inspection en lecture seule de `forms/eures-beta/admin.html`
et `assets/admin/admin-3.js` du dépôt Flask au commit `a95d962` : fonction
`renderMatchingRows`, ligne compacte candidat/employeur/poste/score/statuts,
score global dans la fiche, sous-scores et points forts/faibles.

La liste locale affiche désormais le score sur 100, les statuts du calcul et de
la décision humaine, puis les sous-scores et explications au dépliage. La fiche
montre le score global et les cinq sous-scores directement. Trois rubriques
distinguent points forts, incompatibilités explicites et points à confirmer.
Une évaluation périmée reste signalée. La consultation n’enregistre ni nouveau
calcul ni décision. Les modèles, migrations et règles de score sont inchangés ;
les poids restent expérimentaux, sans seuil automatique ni classement nouveau.
Les coordonnées restent masquées, contrairement aux anciens écrans Flask.

Vérification : 30 tests matching PostgreSQL réussis, contrôles Django/migrations,
HTML et traductions réussis. Les fichiers Python modifiés ont été formatés avec
Black. Contrôle navigateur de la fiche, du dépliage de liste et du petit écran
390 px sans débordement ; scores décimaux sur une seule ligne. Pas d’audit WCAG
exhaustif. Les 537 tests complets de la première implémentation constituent une
vérification antérieure ; la suite complète n’a pas été relancée pour cet affichage.
