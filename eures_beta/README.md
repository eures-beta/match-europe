# Match Europe — parcours locaux

Nouvelle application Django / PostgreSQL / Bootstrap, isolée de l’ancien EURES Beta Flask/Grist. Elle respecte le cadre de `../AGENTS.md`. Aucun changement au serveur FT, à Scalingo ou à Grist.

## Statut

Prototype fonctionnel local, avec quatre rôles fictifs et données persistées dans PostgreSQL. **Ce n’est pas une version prête pour la production.** Les connexions réelles aux services externes sont désactivées ; le démarrage en mode réel est volontairement bloqué.

Les fichiers applicatifs et ressources appartiennent au dépôt public. Les procédures et configurations propres au serveur FT appartiendront au dépôt privé. Aucun secret ou document privé de marque n’est ajouté au dépôt.

## Essayer

Serveur local : <http://127.0.0.1:8014/access/>.

Les boutons des quatre identités fictives permettent de tester les espaces sans mot de passe. Les comptes sont partagés et **ne doivent jamais contenir de données réelles**.

Scénario initial :

1. Conseiller : ouvrir le matching proposé pour l’offre fictive, puis la proposer au candidat.
2. Candidat : ouvrir l’offre, indiquer son intérêt, répondre avec boutons et/ou texte libre, puis accepter la présentation.
3. Employeur : lire les réponses envoyées et accepter la mise en relation.
4. Conseiller : écrire un message de présentation et ouvrir la conversation.
5. Chacun des trois participants : ouvrir la conversation et envoyer des messages. Les autres voient une invitation à actualiser lorsqu’un nouveau message arrive.
6. Administrateur : consulter les rôles et le journal d’actions. Il n’accède pas aux conversations par défaut.

Le scénario initial a été parcouru dans le navigateur jusqu’à l’ouverture de la conversation. Pour recommencer sans modifier les données existantes, créer une nouvelle offre dans l’espace employeur puis simuler son matching depuis l’espace conseiller.

## Parcours avec dépôt

Le conseiller copie les liens d’invitation de son tableau de bord dans sa messagerie habituelle. Ces liens identifient le conseiller et ne donnent accès à aucune donnée privée.

Une nouvelle adresse peut préparer ses brouillons sans être vérifiée. Dans cette première version, elle est renseignée **avant le dépôt**, contrairement à l’ordre envisagé dans la conversation. Une adresse existante doit confirmer l’accès avant de retrouver ses données. Les liens de connexion sont simulés et affichés exclusivement dans la session du navigateur demandeur. Ils expirent après 15 minutes, sont stockés sous forme d’empreinte et consommés atomiquement, uniquement par POST.

Les PDF sont limités à 10 Mo et 30 pages. Lecture dans un processus séparé, durée et temps processeur limités ; original enregistré dans le stockage privé. Un fichier chiffré, illisible ou dépassant les limites est refusé. Les scans sans texte nécessitent une saisie manuelle. Le texte est récupéré, **sans interprétation sémantique par IA** : titre et description peuvent être préremplis, les autres champs sont à compléter. Aucun envoi à un fournisseur d’IA.

L’employeur peut enregistrer plusieurs offres, définir les questions, leurs attentes, les réponses rapides et les conditions indispensables. Deux réponses indépendantes concernent frontaliers et déménagement. Les questions et l’offre sont figées après validation dans cette version ; les modifications ultérieures et le versionnement sont à développer.

Le candidat vérifie son expérience, ses souhaits actuels, sa disponibilité et ses deux formes de mobilité. Son profil est figé après validation dans cette version. La mise à jour et la resynchronisation sont à développer.

Validation et e-mail confirmé sont tous deux nécessaires avant la transmission simulée au matching. Le simulateur présente des profils fictifs : **aucun score n’est calculé, aucun résultat AGLAE n’est prétendu, aucune qualification n’est lancée automatiquement**.

Les réponses peuvent combiner choix et texte libre. Les brouillons sont privés au candidat. L’envoi les rend visibles à l’employeur et au conseiller selon leurs droits. Le conseiller peut demander une clarification. Aucun refus automatique. Les deux accords sont nécessaires pour ouvrir la conversation. Une conversation correspond à un couple candidat–offre.

## Exécution locale

Prérequis : Python 3.12+, PostgreSQL et ses outils (`initdb`, `pg_ctl`, `createdb`), gettext (`msgfmt`).

Depuis ce répertoire :

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run_local.py
```

Le lanceur prépare une base indépendante dans `.runtime/pgdata`, utilise un socket Unix privé, applique les migrations et charge les données fictives de manière idempotente. Il écoute uniquement sur `127.0.0.1:8014`. Aucun port PostgreSQL n’est exposé. Le secret local est généré et conservé dans `.runtime/secret` avec permissions restreintes. Tout `.runtime/` est ignoré par Git.

Pour arrêter l’application : Ctrl+C. La base reste démarrée pour permettre une reprise. Pour l’arrêter :

```sh
pg_ctl -D .runtime/pgdata stop -m fast
```

Configuration PostgreSQL possible via `PGDATABASE`, `PGHOST`, `PGPORT`, `PGUSER`, `PGPASSWORD`. Ne pas les faire pointer vers une base existante contenant des données réelles. Les variables d’accès HTTP sont `ME_ALLOWED_HOSTS`, `ME_CSRF_TRUSTED_ORIGINS` et `ME_HTTPS`. Aucun proxy n’est implicitement considéré fiable.

## Vérifications

```sh
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
.venv/bin/python manage.py test journeys --noinput
```

Les tests utilisent PostgreSQL et créent une base de test distincte, supprimée après exécution. Ils couvrent notamment droits par objet, CSRF, lien à usage unique et expiration, validation avant matching, brouillons, PDF, réponses libres, absence de décision automatique, double accord, confidentialité de la conversation et échappement HTML.

L’interface utilise gettext Django : anglais source, catalogues français et allemand. Les contenus saisis par les utilisateurs et le jeu de données fictif ne sont pas traduits automatiquement. Bootstrap est embarqué localement (licence MIT conservée dans son en-tête) ; aucun CDN n’est requis à l’exécution.

Le logo EURES fourni est copié sans modification. Couleurs de référence : bleu `#00388C`, jaune `#FFE800`, bleu foncé `#081259`, accent employeur `#730A62`. Arial sert de police de substitution. La documentation officielle de marque reste hors du dépôt. Une revue graphique et un audit d’accessibilité complet restent nécessaires avant publication ; aucune certification WCAG AA n’est revendiquée.

## PWA et limites à lever

Manifeste et service worker présents. Les espaces privés, messages et documents **ne sont jamais mis en cache par le service worker**. L’application nécessite une connexion ; l’installation mobile n’a pas encore été vérifiée sur appareils réels. HTTPS sera nécessaire hors de localhost et des icônes PNG dédiées pourront être ajoutées pour les navigateurs qui les exigent.

Notifications internes et détection de nouveaux messages par interrogation périodique. **Pas encore de Web Push, d’e-mail réel, ni de reprise automatique hors connexion.**

Avant un test à distance : préparer un accès HTTPS restreint, examiner les hôtes autorisés, désactiver ou isoler l’accès aux comptes partagés, définir le périmètre fictif et vérifier le parcours sur le poste du testeur. Aucun tunnel ni accès Bruxelles n’est actuellement ouvert.

Avant un raccordement réel : extraction structurée et provenance des champs ; analyse des fichiers et politique de conservation ; validation de l’identité employeur ; envoi d’e-mails et protection anti-abus globale ; connecteur AGLAE et gestion des échecs/idempotence ; géocodage requis par AGLAE ; gestion de la révocation des accès et des départs ; mises à jour des offres/profils ; archivage et suppression ; gouvernance des données, des accords et des sous-traitants ; Web Push ; sauvegarde et restauration ; audit de sécurité et d’accessibilité. La seconde authentification n’est pas implémentée à ce stade.

Cette liste décrit le travail restant : le prototype ne doit pas être déployé tel quel sur FT.

## Parcours employeur fonctionnel local (15 octobre 2026)

Le serveur statique 8015 est remplacé par Django. Lancement depuis ce dossier :

```sh
ME_EMPLOYER_LOCAL_API=1 ME_LOCAL_PORT=8015 .venv/bin/python run_local.py
```

Ouvrir `http://127.0.0.1:8015/previews/employer-landing/import-fr.html`. La landing conserve ses fichiers générés, mais ses interactions sont réellement reliées au serveur lorsqu’il injecte `data-live-local=true`. Le mode statique reste une maquette distincte, non fonctionnelle côté réseau.

- POST `/local-api/imports/` : après email et accord, lecture HTTPS publique ou PDF (10 Mo, 30 pages), ou saisie manuelle. Brouillon PostgreSQL session-owned ; aucun usage des comptes fictifs partagés.
- GET `/local-api/imports/` et `/<uuid>/` : reprise des brouillons uniquement dans la même session. L’email n’est pas une authentification : changer de navigateur ne permet pas de retrouver le brouillon. Aucun email réel envoyé.
- POST `/<uuid>/` action `save` : modifications enregistrées avec contrôle de révision ; action `locate` : géocodage Nominatim/OpenStreetMap du lieu public, proposition de point à confirmer ; action `validate` : champs contrôlés côté serveur, confirmation et lieu requis avant l’envoi réel.
- AGLAE : origine sandbox fixée côté serveur ; clé lue depuis le fichier privé désigné par `AGLAE_SANDBOX_KEY_FILE` ou `~/.config/match-europe/aglae-sandbox.key`. Aucun secret dans les pages, la base ou les logs. UUID stable, sérialisation PostgreSQL et lecture du retour après envoi.
- Envoi d’offre inactive et des questions ; les critères indispensables restent destinés à la revue humaine locale (`isMandatory=false` chez AGLAE). Aucune route de matching, qualification, candidat ou SMS appelée. En cas d’échec, les corrections restent sauvegardées et le succès n’est pas annoncé.
- Protection URL : HTTPS/443, pas d’identifiants, refus de toute résolution privée ou multicast, connexion TLS épinglée à l’IP validée, contrôle de chaque redirection, limites de taille et de temps ; pas de proxy ni d’exécution JS. Un site anti-robot comme Moovijob peut refuser : PDF ou copier-coller restent disponibles.
- Extraction : données JobPosting JSON-LD lorsqu’elles sont présentes ; sinon titre et texte de la page. PDF : texte effectivement extrait dans un sous-processus limité. Pas d’analyse sémantique IA ni de données inventées : compléter les champs absents.
- Brouillons et emails conservés localement dans PostgreSQL. Originaux PDF non conservés par ce nouveau flux. Aucun téléchargement automatique ni envoi de l’email à AGLAE. Aucune aptitude production ou conformité juridique complète revendiquée ; ne pas exposer ce serveur hors boucle locale.

Migration additive `0002_employerimport`. Tests : 31 tests PostgreSQL passés, mocks réseau pendant tests automatisés. Essais réels distincts : lecture Lever, PDF de test, sauvegarde/reprise navigateur ; offre fictive enregistrée puis relue inactive avec une question dans la sandbox (identifiant de test non publié). Offre Moovijob antérieure inactive inchangée. Aucun push ni déploiement.

Mise à jour ergonomie : POST `/local-api/imports/source/` lit et vérifie l’URL avant la demande d’email, après accord de lecture sur cet écran. Le résultat est lié à la session et réutilisé via un jeton à usage unique pendant 15 minutes lors de la création du brouillon ; il ne peut pas être substitué par une autre URL. Le PDF/coller reste disponible directement dans l’encadré d’erreur. Tests ciblés : 15 passés.

Ordre corrigé : après email et accord explicite, la création tente un premier POST d’offre inactive + GET de relecture AGLAE. `initial_sent_at` (migration 0003) ouvre l’écran de vérification. Si poste/entreprise/lieu/description sont absents, l’écran de préparation demande seulement ces champs puis l’action `prepare` réalise l’envoi initial. Les corrections restent en brouillon jusqu’à l’action finale `validate` qui met à jour l’offre et les questions et relit le retour. La validation finale est refusée côté serveur sans envoi initial. Aucun matching ou SMS. 34 tests PostgreSQL passés, dont ordre POST/GET avant vérification.

Lecture France Travail : les pages `/offres/recherche/detail/<id>` utilisent un composant dynamique `descriptif-offre`. Le lecteur suit désormais la ressource JSON publique utilisée par ce composant, `/api-descriptifoffre/offre/<id>`, avec les mêmes protections HTTPS/IP, sans jeton. Mapping titre, lieuTravail (jamais adresse agence), organisme annonceur, contrat, salaire, expérience et compétences ; pas de recommandations voisines dans la description. Source non contractuelle susceptible d’évoluer ; échec explicite si schéma/ID ne correspond pas. Offre réelle 215HBDL relue : titre et lieu corrects, aucun nouvel envoi AGLAE pendant le diagnostic. Les anciens brouillons conservent leurs données : réimporter le lien pour appliquer l’extraction corrigée.

Lecture PDF avant email : le bouton « Lire ce PDF » vérifie le document après accord explicite, puis conserve uniquement le résultat extrait en session pendant 15 minutes. La création du brouillon consomme un jeton à usage unique ; aucun second transfert PDF. Un PDF illisible reste à l’étape fichier, sans demander d’email. FR/EN/DE, V1 et V2.

Correction extraction PDF : ignore les puces isolées dans le titre, normalise le caractère de police ɑ, reconnaît un en-tête compact poste/entreprise/code postal et ville, les champs explicitement étiquetés FR/EN/DE et un contrat CDI/CDD non ambigu. Aucun employeur ou lieu inventé si la structure ne correspond pas. 26 tests ciblés passent ; essai local sur le PDF fourni, sans envoi externe pendant la vérification. Les brouillons existants doivent être réimportés.

## Contact entreprise et espaces existants (16 octobre 2026)

Le parcours d’import local recueille un contact distinct de l’email d’accès : nom et email obligatoires, téléphone et fonction facultatifs. L’email du contact est prérempli depuis l’email saisi, puis reste modifiable. Le bloc est traduit FR/EN/DE et réutilise les styles employeur existants. L’employeur peut corriger le contact à la préparation, à la vérification et après enregistrement, ainsi qu’en reprenant un ancien brouillon.

`EmployerImport.contact` est séparé de `data` ; aucune copie de ces champs dans les requêtes AGLAE ou les exports de fiche. La migration additive `0004_employer_contact_and_adviser` conserve les anciens brouillons et laisse leurs contacts à compléter. Les éventuelles coordonnées déjà présentes dans le texte libre de l’annonce ne sont pas automatiquement expurgées.

Les tableaux de bord existants affichent une section « Offres employeur importées ». Depuis `/access/`, choisir le rôle de démonstration administrateur pour voir les imports et attribuer un conseiller actif et vérifié. Le conseiller affecté et les administrateurs vérifiés peuvent consulter `/imported-offers/<uuid>/` ; candidats, autres employeurs et autres conseillers sont refusés côté serveur. L’administrateur peut changer ou retirer l’affectation. Aucun rattachement automatique à une identité partagée ni à un conseiller arbitraire. Les imports restent des objets distincts des `Offer` du scénario de démonstration : ce raccordement donne accès au suivi/contact, sans lancer matching, préqualification ou conversation.

API propriétaire de session : `POST /local-api/imports/` exige désormais `contact` (objet JSON sérialisé : `name`, `email`, `phone`, `function`). La réponse propriétaire contient `contact`, avec email prérempli pour les anciens imports. `POST /local-api/imports/<uuid>/` accepte `action=contact`, `revision` et `contact`, sans modifier l’état de validation de l’offre ni appeler AGLAE ; les conflits de révision sont refusés. La validation finale exige un contact enregistré complet. Aucun email réel ni relance automatique n’est ajouté.

La notice historique reste signalée comme non validée pour le nouveau parcours ; un encadré décrit le contact dans l’essai local. La politique de conservation et l’authentification de production restent à définir. Les accès démo partagés ne conviennent pas à des données personnelles réelles.
