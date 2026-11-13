## Mise à jour — 9 novembre 2026

Le dialogue Albert fonctionne dans tous les environnements, avec une clé privée configurée ; il est actif par défaut. La simulation est explicitement choisie pour les essais, jamais imposée par l’environnement. Les appels envoient uniquement la condition de l’offre, les déclarations correspondantes, les paroles et l’historique utile du dialogue ; aucune transmission automatique à l’employeur ni modification de profil sans relecture explicite. La CSRF, la vérification de la propriété de la demande, les quotas et les contrôles de version sont conservés. Sans clé ou en cas d’échec, le formulaire guidé reste disponible. Les anciennes restrictions locales ci-dessous sont remplacées.

# Dialogue Albert simulé — prototype local

## Périmètre

Eric confirme le 8 novembre 2026 : Albert accompagne la confirmation d’une offre
et les propositions de mise à jour du profil qui découlent des réponses du
candidat. La création initiale du profil est exclue. Prototype local simulé
autorisé ensuite. Base de livraison GitHub vérifiée : #162, `20df0b7`.
Branche locale `codex/albert-confirmation-dialogue-simulated` ; aucune publication,
fusion, modification de #162 ou activation en production dans ce lot.

Le mot « simulé » est affiché dans l’interface. Aucun modèle ni service externe
n’est appelé. Le simulateur ne comprend pas le langage naturel : il reconnaît
un corpus volontairement restreint en FR/EN/DE, pour tester l’orchestration avant
de concevoir un vrai raccordement Albert. Une phrase hors corpus reste sans
classification, avec demande de précision et possibilité de formulaire guidé.

## Parcours démontré

1. Conseiller : soumettre une offre depuis les confirmations existantes.
2. Candidat : ouvrir la question puis « Essayer le dialogue Albert simulé ».
3. Répondre librement. Le simulateur reconnaît `oui` / `yes` / `ja` et
   `non` / `no` / `nein` pour la condition courante.
4. Sur une question exigeant le samedi, `un samedi sur deux` / `every other
   Saturday` / `jeden zweiten Samstag` demande de préciser la portée. Avec
   « Cette offre uniquement », il propose une réserve sans modifier le profil.
5. `je ne suis plus disponible le samedi` / `I am no longer available on
   Saturdays` / `Ich bin samstags nicht mehr verfügbar`, avec « Mon profil
   général », propose de retirer les créneaux déclarés du samedi. Aucun autre
   champ n’est interprété automatiquement.
6. Le candidat relit la reformulation et peut corriger ou annuler. Une validation
   POST distincte est nécessaire pour enregistrer une réponse.
7. Pour le changement général, une case explicite prépare un brouillon du
   profil avec le samedi décoché. Le profil durable reste inchangé. Le candidat
   complète ses nouveaux créneaux dans l’étape Conditions, vérifie la cohérence
   des conditions de travail, relit le profil puis l’enregistre explicitement.
   Si samedi était la seule disponibilité, la relecture ne peut pas être sautée.
8. Le profil mis à jour invalide les confirmations concernées et l’accord
   antérieur selon les règles existantes. L’accord de transmission reste dans
   le formulaire guidé séparé ; aucun envoi n’est implémenté.

Une suppression de créneau n’exprime pas à elle seule une indisponibilité
exclusive : le candidat doit vérifier « Ce sont mes seules disponibilités » et
ses autres choix dans le formulaire existant. Le simulateur ne déduit pas de
nouvelles disponibilités et ne supprime pas automatiquement les autres conditions.

## Accès et données

`ALBERT_SIMULATED` est désactivé par défaut. La route conserve
les gardes locales existantes : loopback, données fictives, comptes actifs,
candidat propriétaire, profil vérifié et offre validée. Pas d’accès implicite
employeur, conseiller ou superutilisateur ; pas d’emails réels ni mode production.

Réponse limitée à 2000 caractères. Proposition signée, limitée à quinze minutes,
liée au candidat, à la demande, au contexte offre/profil/réponses et à la version
de la réponse. Une proposition périmée, altérée ou déjà consommée ne peut pas
écraser une réponse récente. Les accès sont vérifiés à nouveau lors de la validation.
La relecture du profil issue du dialogue contient aussi sa version initiale :
une modification concurrente du profil provoque un refus 409 et une nouvelle
relecture, sans écraser la version récente.

Pas de table ni de migration ajoutée. Pas d’historique libre de conversation
stocké côté serveur : proposition signée dans le formulaire, puis seulement la
réponse explicitement validée dans `CandidateOfferReviewAnswer`. Le brouillon utilise
la session existante du profil, avec sa durée de vie habituelle. Réponses privées
sans cache, POST/CSRF, textes échappés et paramètres POST sensibles masqués dans
les pages de débogage. La rétention et la purge pour un usage réel restent à définir.

## Essayer et vérifier

Environnement local isolé déjà préparé pour #162 ; voir
[les confirmations](CANDIDATE_OFFER_CONFIRMATIONS.md) pour PostgreSQL et les comptes.

- `make matching-translations` : compiler FR/DE.
- `make matching-seed` : préparer les paires fictives dans une base d’essai.
  Un conseiller de recette habilité sollicite la confirmation depuis le détail de la paire.
- `make run PORT=9044` : serveur sur loopback, port 9044. Pour simuler sans Albert réel,
  définir `ALBERT_SIMULATED=1` dans le `.env` du worktree.
- `make test TESTS=tests.matching.test_dialogue` : protections, corpus trilingue, validation et mise à jour
  complète du profil sur PostgreSQL jetable.
- `make test`, `make check`, `make format-check`, `make format-html-check`,
  `make translations-check` : suite et contrôles existants.
- En copie isolée : `make translations-extract`, puis `make translations-check`
  pour vérifier les textes effectivement extraits.

Le véritable dialogue Albert, la compréhension d’autres réponses, les propositions
sur d’autres champs, la transmission réelle, la production et l’audit WCAG exhaustif
restent hors de ce prototype. L’interface et les actifs EURES existants sont réutilisés.

## Vérifications exécutées

9 tests dialogue et 591 tests PostgreSQL complets réussis ; Django/migrations,
Black, format/structure HTML et traductions vérifiés, y compris extraction suivie
du contrôle dans une copie isolée. Navigateur : précision de portée, réserve,
proposition de retrait du samedi, complétion des disponibilités et enregistrement
explicite du profil fictif vérifiés. Pages FR/EN/DE, conservation de la question
lors du changement de langue, navigation au clavier et largeur mobile 390 px
sans débordement vérifiées. Pas d’audit WCAG exhaustif ni de vérification d’un modèle réel.

Lors de la recette, le candidat fictif A a validé lundi matin comme seules
disponibilités et travail en journée après retrait du samedi ; ces modifications
de données jetables sont conservées. Les tests automatisés ont leur propre base.
