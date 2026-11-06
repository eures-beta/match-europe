# EURES beta / Match Europe — vue d’ensemble

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

Parcours commun avec/sans CV en cinq étapes, lecture locale et brouillon temporaire. Aucun compte ou raccordement au matching. Voir [périmètre et recette](CANDIDATE_LOCAL_JOURNEY.md).


## Questionnaire candidat simplifié — état local actuel

La proposition initiale avec CV est remplacée à la demande d’Eric : questionnaire sans import ni historique professionnel, avec recherche ESCO/ROME, mobilité/langues, conditions et relecture. Voir [recette et limites](CANDIDATE_LOCAL_JOURNEY.md). Aucun raccordement au matching ou compte durable.
