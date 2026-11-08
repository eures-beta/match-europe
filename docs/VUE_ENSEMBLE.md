## 9 novembre 2026 — correction de la parité des environnements

La décision d’Eric remplace les anciennes limites de prototype ci-dessous : les fonctionnalités métier sont destinées au local, aux recettes et à la production, avec les mêmes droits. L’import Albert est actif par défaut, sans dépendance au mode démo ni aux e-mails. Une clé privée reste nécessaire aux appels réels ; le repli manuel est conservé. Les outils fictifs restent isolés. Aucune fusion ni opération de production n’est réalisée par cette correction.

## 9 novembre 2026 — profil du compte employeur (#133)

À la demande de dejafait, `EmployerResponsePractice` devient `EmployerProfile`,
avec le champ `user` et l'accès inverse `user.employer_profile`, en parallèle de
`CandidateProfile`. Il décrit le compte personnel, pas l'entreprise. Relation
zéro ou un profil par compte, créée lors des premières réponses ; aucune création
automatique. Migration de renommage réversible, sans perte des réponses existantes.
Les questions, l'API, les droits et les règles de validation restent inchangés.

## 8 novembre 2026 — portefeuille conseiller partagé et décision manuelle (local)

Eric autorise le portefeuille partagé par équipe et le matching manuel malgré
un score faible. Implémentation locale sur `codex/team-matching-local`, dans la
continuité des deux commits locaux au-dessus de #159 ; aucune publication distante.

Avec `MATCHING_TEAMS_ENABLED=1` (désactivé par défaut), l’espace conseiller
`/accounts/dashboard/` présente les seules paires attribuées aux équipes actives
du conseiller. Adhésion, droit de décision et attribution des offres et candidats
sont vérifiés en lecture et à chaque écriture. Les anciennes routes anonymes
d’opérateur sont fermées dans ce mode. Les comptes employeurs et invitations
restent accessibles avec leurs droits existants.

Préparation manuelle : choisir candidat/offre dans le portefeuille, calculer,
examiner, puis retenir avec un motif professionnel obligatoire. Un score nul
reste nul ; aucun blocage explicite ne peut être contourné. Historique avec
compte auteur, équipe, date, calcul et motif ; recalcul sans effacer la décision.
Les décisions simultanées ou issues d’un écran périmé sont refusées explicitement.

Migration additive `matching.0002` appliquée à la base de recette. Modèles d’équipes,
adhésions et attributions explicites ; pas d’interface de gestion des équipes dans
ce lot. `make matching-team-seed` prépare deux conseillers de la même équipe,
un conseiller d’une autre équipe et un scénario à score nul sans écraser les
décisions existantes. `make matching-run` active ce mode uniquement sur loopback.
Entrée : `/accounts/test-accounts/`, puis conseiller de test. Tout est fictif ;
aucun message, Albert réel, transmission ou consentement candidat implémenté.

Vérification du lot : 557 tests PostgreSQL réussis, dont 18 tests dédiés aux équipes et décisions manuelles ; contrôles Django/migrations, Black, djLint, structure HTML et traductions FR/DE réussis. Contrôle HTTP réel des pages FR/EN/DE, du formulaire manuel et de la liste employeurs/invitations réussi. Le navigateur automatisé est indisponible : contrôle visuel du nouveau tableau non réalisé.

## 8 novembre 2026 — scores et résultats du matching visibles

TRANSVERSE : Eric demande une présentation comparable à Flask. Lecture de
l’administration Flask puis adaptation locale : ligne candidat/employeur/poste,
score global /100 visible, sous-scores, statuts et trois rubriques d’explication.
Aucune modification des poids, blocages, décisions ou droits. Trente tests matching
PostgreSQL réussis, contrôle navigateur et petit écran 390 px. Aucun envoi,
publication ou déploiement distant. Voir [le contrat de matching](MATCHING.md).

## 7 novembre 2026 — matching local autorisé

TRANSVERSE / CANDIDATS / EMPLOYEURS : Eric autorise le matching local avant
l’outil conversationnel. Base de pile #159 (`c39c728`) vérifiée ; aucune publication,
fusion ou recette distante autorisée. Correspondances, inconnus, trois blocages
explicites et décisions humaines distinctes. Métier hors score ; poids expérimentaux,
pas de classement ni seuil de rejet validé. Albert et ses confirmations par offre
ou générales restent à développer. Voir [contrat et recette](MATCHING.md).

## 7 novembre 2026 — parcours continus de recette

EMPLOYEURS / CANDIDATS : raccordement local des compétences ESCO dans les formulaires habituels, conservation dans les offres et profils, recette unique depuis l’accueil. Albert simulé, données fictives, confirmation candidat privée de session. Base de pile #157 vérifiée, pas de production. Voir [recette continue](CONTINUOUS_JOURNEYS.md).

## 6 novembre 2026 — métiers hors sélection, essai local

TRANSVERSE / EMPLOYEURS / CANDIDATS : recherche d’un métier ESCO hors des 50 fiches, préparation serveur des suggestions parmi ses relations officielles vérifiées, cache PostgreSQL partagé et choix temporaires par rôle. Simulation par défaut, accès loopback uniquement ; aucun raccordement aux offres/profils réels ni appel Albert réel. Voir [contrat et recette](ALBERT_SKILLS.md).

# EURES beta / Match Europe — vue d’ensemble

## 6 novembre 2026 — projet candidat sans métier

CANDIDATS : mode ouvert dans la première étape du questionnaire, trois listes ESCO transversales et réponses raccordées à la confirmation email puis au profil privé. Migration additive, anciens profils conservés sans compétences inventées. Parcours métier et pilote employeur conservés ; aucun matching ni nouveau droit. Voir [périmètre](CANDIDATE_OPEN_SKILLS.md).

## 6 novembre 2026 — extension locale proposée à 50 métiers

TRANSVERSE / EMPLOYEURS / CANDIDATS : préparation de deux JSON compatibles avec
le pilote #154, sept métiers existants conservés et 43 ajouts officiels ESCO 1.2.1.
La liste et les sélections éditoriales restent proposées à Eric. Aucun profil,
offre ou matching raccordé ; mêmes protections de recette locale. Voir
[liste et identifiants](SKILLS_CATALOGUE_50.md) et [contrôles](SKILLS.md).

## 6 novembre 2026 — pilote local des compétences

TRANSVERSE / EMPLOYEURS / CANDIDATS : parcours de recette autonome dans Django,
`/skills-pilot/`, désactivé par défaut et réservé au loopback local. Six métiers,
références ESCO FR/EN/DE partagées et sélections temporaires distinctes. Aucune
connexion aux offres, profils durables, conseillers ou matching existants.
La validation utilisateur et le push sont à venir. Voir [périmètre et recette](SKILLS.md).

## 6 novembre 2026 — essai Albert pour les offres employeurs

Essai opt-in local/recette de structuration du texte PDF ou collé par Albert, suivi de recherches ESCO/ROME indépendantes et de la relecture employeur. Désactivé par défaut, interdit en production. Aucun changement candidat ni matching. Voir [périmètre et limites](ALBERT_IMPORT.md).

## 5 novembre 2026 — réponses habituelles des employeurs

Le parcours employeur conserve les pratiques de réponse dans une fiche dédiée
par compte et les réaffiche aux prochains dépôts. Aucun partage implicite entre
collègues d'un établissement. Les relances restent à développer. Voir
[le périmètre et les limites](EMPLOYER_RESPONSE_PRACTICE.md).

## 4 novembre 2026 — premier lot candidat

Le modèle `users.User` accepte désormais `kind=candidate`. Son ajout ne crée
pas encore de profil persistant : le questionnaire reste temporaire en session.
Le candidat ne reçoit aucun droit employeur ou conseiller. Voir
[le périmètre et la migration](USER_MODEL.md).
Le stockage futur des réponses utilisera des champs et tables dédiés, selon
le choix d’Eric ; la création du compte à la fin du questionnaire et la
vérification par email restent à développer.

## 2 novembre 2026 — retrait du premier prototype

Les quatre parcours de `/access/` sont retirés, avec leurs connexions fictives,
vues, templates et initialisation automatique. Le prototype actuel reste celui
de l’accueil public, du candidat à trois choix et de l’import employeur trilingue.
Les descriptions historiques de matching/conversations ci-dessous décrivent des
travaux antérieurs, pas des fonctionnalités actuellement exposées.
Voir [le périmètre, le nettoyage des comptes et le stockage](LEGACY_PROTOTYPE_RETIREMENT.md).

Les migrations actuelles sont maintenant autonomes dans `employers`.
Le dossier d'archives et ses applications de compatibilité sont supprimés dans
le second lot, à déployer après confirmation du marqueur de transition.
Voir [le guide des deux déploiements](AUTONOMOUS_MIGRATIONS.md).

Référence commune créée le 16 octobre 2026 à partir des README et de HANDOFF.md. Ce document décrit le cadre produit ; il ne constitue pas une vérification de production.

## Objectif et périmètre

Organiser les parcours employeur, candidat, conseiller et administrateur pour préparer une mise en relation explicable, avec validation humaine et accords des participants.

Deux implémentations coexistent :

- **EURES beta historique** : Flask/Grist, formulaires, statistiques et administration/suivi. Voir le dépôt historique [eures-beta/eures-beta](https://github.com/eures-beta/eures-beta).
- **Match Europe local** : Django/PostgreSQL/Bootstrap dans `eures_beta/`, pour essayer les nouveaux parcours. Voir [documentation locale](../eures_beta/README.md). Ce prototype n’est pas prêt pour la production.

## Les quatre volets

| Volet | Responsabilité et parcours | Liens avec les autres volets |
| --- | --- | --- |
| EMPLOYEURS | Préparer/importer une offre, vérifier ses informations et son contact, définir les questions, examiner les réponses et accepter la présentation. | Le conseiller suit les offres attribuées ; le candidat répond ; les accords ouvrent la conversation. |
| CANDIDATS | Préparer un profil, préciser souhaits et mobilité, manifester un intérêt, répondre aux questions et accepter la présentation. | Le conseiller accompagne la qualification ; l’employeur reçoit les réponses selon les droits. |
| CONSEILLERS | Examiner les propositions, demander des précisions, accompagner la mise en relation et participer à la conversation. | Accès limité aux objets et participants autorisés ; suivi des imports attribués par l’administration. |
| ADMIN | Superviser les accès et activités autorisées, attribuer ou retirer un conseiller sur un import. | Droits spécifiques à vérifier par objet ; le rôle admin ne donne pas par défaut accès à toutes les conversations. |

Ces volets sont des domaines fonctionnels et des préfixes de discussions, pas quatre projets indépendants ni une nouvelle organisation imposée au code.

## Organisation actuelle du code

- `employers` : six modèles, dont `Company`, `CompanyMembership` et `JobOffer`, pour les espaces employeurs, leurs membres et leurs offres ;
- `candidates` : questionnaire et modèle `CandidateProfile` pour ses réponses
  durables ; le parcours de démonstration reste en session, sans raccordement
  à ce stockage. Voir [le périmètre du modèle](CANDIDATE_PROFILE_STORAGE.md) ;
- `documents` : lecture et extraction PDF, sans ancien modèle de fichier stocké ;
- `occupations` : catalogue métiers partagé ;
- ressources et vues publiques communes directement dans `eures_beta`.

Les anciens parcours ne sont plus des applications installées. Leur historique
de migrations n'est plus nécessaire après la transition des bases conservées.
Les tables employeur actuelles gardent leurs noms physiques `journeys_employer*`.

## Parcours et limites à distinguer

La lecture d’offres par URL possède des adaptateurs publics ciblés pour France
Travail et EURES, sans navigateur ni authentification externe. Voir
[leur fonctionnement, protections et limites](OFFER_URL_IMPORT.md).

Les pages employeur consolidées utilisent les templates Django et les catalogues
gettext plutôt que trois copies HTML par langue. Voir [les pages concernées et les limites restantes](EMPLOYER_TRANSLATIONS.md).

- Le scénario de démonstration relie offre, candidat, préqualification, double accord et conversation à trois avec des données fictives.
- Le parcours employeur d’import possède ses propres brouillons et objets `JobOffer`. Leur affichage aux conseillers/admins ne les convertit pas en `Offer` et ne lance pas le matching.
- Le scénario initial simule les services externes. Le nouveau parcours employeur peut lire des sources publiques, géocoder et envoyer/relire une offre inactive dans AGLAE sandbox lorsque configuré. Ne pas résumer tous les parcours comme entièrement simulés.
- E-mails réels, intégration complète, habilitations de production et conformité complète ne sont pas acquis.

## Références et organisation des discussions

- [Décisions communes](DECISIONS.md) : choix validés et contraintes.
- [État du projet](../HANDOFF.md) : travaux documentés, validations datées, limites et suites.
- [AGENTS.md](../AGENTS.md) : règles de travail obligatoires.

Noms de discussions : `EMPLOYEURS — Sujet`, `CANDIDATS — Sujet`, `CONSEILLERS — Sujet`, `ADMIN — Sujet`, ou `TRANSVERSE — Sujet`.

Les discussions ne constituent pas une mémoire automatiquement partagée. Conserver dans ces références les informations nécessaires à une reprise ; consulter les fichiers concernés avant toute modification.

## Recette locale employeurs — lot 3 (22 octobre 2026)

L’espace des imports employeurs permet de retrouver les offres des établissements
habilités, les consulter, les modifier avant recherche et les dupliquer. Le
verrouillage repose sur une date serveur distincte ; le lancement effectif de la
recherche reste à raccorder dans un lot suivant. Aucun nouveau résultat candidat
ni modification des espaces conseillers/admins.
Voir [périmètre et recette](EMPLOYER_OFFER_WORKSPACE.md).

## Lot 4A employeur — lancement simulé (22 octobre 2026)

Confirmation de recherche incluant qualification/contact, gestion des échecs et
états incertains, sans appel réel ni nouvelle candidature/conversation.
Clôture et archivage restent à définir. Voir [lot 4A](EMPLOYER_SEARCH_LAUNCH.md).

## Accueil candidat — 28 octobre 2026

Premier écran repris dans la structure Django actuelle, trois entrées simulées
CV/LinkedIn/saisie manuelle en FR/EN/DE. Aucun raccordement au matching, aux
conseillers ou aux données candidat. Voir [périmètre](CANDIDATE_LANDING.md).

La PR #63 conserve un seul template gettext, ses statiques et tests dans
`candidates`. Le contrôle d’accès de démonstration est partagé dans
`eures_beta/demo_access.py`, sans dépendance à une API employeur ni modification
des restrictions. Le générateur candidat et son dictionnaire trilingue sont retirés.

## Catalogue partagé ESCO/ROME — 29 octobre 2026

Le paquet `eures_beta/occupations` fournit des références et recherches métiers
locales versionnées, indépendantes des applications métier. Aucun import CV ni
interface candidat ajouté. Voir [catalogue et limites](OCCUPATION_CATALOG_MAINTENANCE.md).

## Métier dans la relecture employeur — 29 octobre 2026

La fiche d’import employeur utilise le catalogue partagé et conserve les choix
explicites dans son brouillon. Template unique et gettext, aucun parcours candidat
ajouté. Voir [contrat et limites](EMPLOYER_OCCUPATIONS.md).


## Proposition locale candidat — 2 novembre 2026

Parcours commun avec/sans CV en cinq étapes, lecture locale et brouillon temporaire. Aucun compte ou raccordement au matching. Voir [périmètre et recette](CANDIDATE_JOURNEY.md).


## Questionnaire candidat simplifié — état local actuel

La proposition initiale avec CV est remplacée à la demande d’Eric : questionnaire sans import ni historique professionnel, avec recherche ESCO/ROME, mobilité/langues, conditions et relecture. Voir [recette et limites](CANDIDATE_JOURNEY.md). Aucun raccordement au matching ou compte durable.
## 7 novembre 2026 — lisibilité du projet candidat ouvert

Sur #158, préparation d’une évolution : secteurs repliables affichés d’emblée dans les listes techniques et savoir-être présentés en phrases concrètes, un par ligne. Même catalogue et mêmes choix enregistrés. Voir [le contrat du parcours](CANDIDATE_OPEN_SKILLS.md).
