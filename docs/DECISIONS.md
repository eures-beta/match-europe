## 13 novembre 2026 — noms explicites des modèles de rapprochement et revue

Choix validé par dejafait dans la PR #162 : `MatchPair` devient
`CandidateOfferMatch`, `ConfirmationRequest` devient `CandidateOfferReview`,
`ConfirmationAnswer` devient `CandidateOfferReviewAnswer` et
`TransmissionAgreement` devient `CandidateProfileSharing`. Le dernier nom
n’inclut ni Consent ni Decision ; il conserve aussi les refus et retraits.
Les trois modèles de revue restent séparés. Migration réversible supplémentaire,
tables physiques et données existantes conservées, migrations historiques inchangées.

## 13 novembre 2026 — droits métier identiques pour les conseillers

Décision de dejafait : tous les conseillers connectés et actifs ont les mêmes
droits métier. Le matching, les demandes de confirmation candidat et les invitations
employeurs ne demandent plus de permissions Django ou de groupe supplémentaires.
Les rôles candidat/employeur, la désactivation des comptes, la propriété du profil,
la validation des données et CSRF restent contrôlés. L'administration Django garde
ses protections distinctes. Aucun renommage de modèle dans ce correctif.

## 13 novembre 2026 — un seul serveur de développement

TRANSVERSE : utiliser `make run PORT=…` pour tous les parcours Django, avec un
port libre, une base et un `.env` propres à chaque worktree. Les huit variantes
de démarrage par domaine sont retirées. Le port ne choisit aucune simulation ;
les réglages restent explicites dans le `.env`. Les dispositifs WSGI et les
tests restent distincts. Voir [le guide de développement](DEVELOPPEMENT.md).

## 13 novembre 2026 — sélection des tests sans multiplication des cibles

TRANSVERSE : à la demande de dejafait, une entrée Django `make test` avec
`TESTS` et `TEST_ARGS`, et une entrée Node `make test-js` avec `JS_TESTS`.
Les sélections par fonctionnalité ne créent plus de cible supplémentaire.
Les bancs Docker et le diagnostic de mise à niveau restent distincts.
Documentation, consignes agents et CI utilisent ces mêmes entrées ; aucun
changement métier ou de données. Voir [les exemples](TESTS.md).

## 13 novembre 2026 — retrait des trois modèles employeurs hérités

EMPLOYEURS / ADMIN : après retrait des parcours obsolètes, suppression de
EmployerEmailLink, EmployerSearchOperation et EmployerSearchEvent et de leur
administration. La migration employers.0007 exige trois tables vides et refuse
sinon toute suppression ; les migrations historiques restent en place.
Company, CompanyMembership, EmployerProfile et JobOffer sont conservés.
Le verrouillage par search_started_at reste actif, sans les états du simulateur.
Aucune fusion ni intervention sur une base distante par ce changement.
Voir [le contrat de retrait](EMPLOYER_SEARCH_LAUNCH.md).

## 10 novembre 2026 — suppression des parcours de démonstration hérités

Demande explicite de dejafait : nettoyage agressif dans une nouvelle PR au sommet
de la pile, sans fusion ni production. Retirer les parcours obsolètes et les cinq
réglages de présentation discutés, sans exposer leurs anciennes routes en levant
leurs protections. Les comptes fictifs restent des outils de test isolés.
Les données historiques sont conservées et les accès réels gardent leurs contrôles.
Cette décision remplace les consignes d'activation des modes de démonstration
figurant dans les entrées historiques ci-dessous.

## 9 novembre 2026 — livraison dans tous les environnements

Décision d’Eric : retirer les restrictions arbitraires local/recette/production des fonctionnalités métier. Configuration et droits réels conservés, fonctionnalités actives par défaut, simulations explicites. Autorisation explicite reçue pour les trois usages Albert, les accès propriétaires employeur et le transport commun des e-mails configuré dans chaque environnement. La pile distante a été actualisée sans perdre les correctifs publiés en parallèle. Validation locale : 605 tests PostgreSQL réussis après intégration du client Albert partagé ; aucun appel Albert ou e-mail réel, aucune fusion ni opération de production. Voir [le contrat actuel et les prérequis](ENVIRONMENT_PARITY.md).

## 9 novembre 2026 — correction de la parité des environnements

La décision d’Eric remplace les anciennes limites de prototype ci-dessous : les fonctionnalités métier sont destinées au local, aux recettes et à la production, avec les mêmes droits. L’import Albert est actif par défaut, sans dépendance au mode démo ni aux e-mails. Une clé privée reste nécessaire aux appels réels ; le repli manuel est conservé. Les outils fictifs restent isolés. Aucune fusion ni opération de production n’est réalisée par cette correction.

## 9 novembre 2026 — profil du compte employeur (#133)

À la demande de dejafait, `EmployerResponsePractice` devient `EmployerProfile`,
avec le champ `user` et l'accès inverse `user.employer_profile`, en parallèle de
`CandidateProfile`. Il décrit le compte personnel, pas l'entreprise. Relation
zéro ou un profil par compte, créée lors des premières réponses ; aucune création
automatique. Migration de renommage réversible, sans perte des réponses existantes.
Les questions, l'API, les droits et les règles de validation restent inchangés.

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

## 7 novembre 2026 — publication et recette regroupée autorisées

Eric demande une nouvelle PR au-dessus de #157, une recette jetable de sept jours de cette PR et la fermeture de la recette de #157. Raccordement étendu à preview HTTPS explicite, données fictives, Albert simulé et e-mails réels désactivés. Aucune fusion ou production autorisée.

## 7 novembre 2026 — parcours continus de recette

Eric confirme le raccordement employeur et candidat pour tester un parcours continu reprenant la pile ouverte. Préparation locale au-dessus de #157, simulation Albert et e-mails réels désactivés. Aucun matching, fusion, déploiement ou nouvelle publication autorisé par cette étape. Voir [périmètre et données](CONTINUOUS_JOURNEYS.md).

## 6 novembre 2026 — lot local compétences et Albert autorisé

Après l’audit en lecture seule de #156, Eric accepte le lot local proposé, désactivé par défaut et testé sans service payant. Implémentation dans le pilote commun : confirmation du métier, message d’attente, sélection parmi les compétences officiellement reliées dans ESCO, persistance et réutilisation. Hypothèse d’implémentation annoncée : aucun nouveau lien ESCO ni savoir-être inféré. La pertinence réelle d’Albert et le raccordement aux questionnaires durables restent à valider. Aucun push, fusion ou déploiement autorisé par cet accord. Voir [contrat](ALBERT_SKILLS.md).

# EURES beta / Match Europe — décisions communes

## 6 novembre 2026 — candidat ouvert à différents métiers

Eric autorise l’implémentation dans une nouvelle PR, sans fusion ni déploiement, après l’audit de #155. Parcours sans métier : un écran à trois sections repliables, savoir-faire 0–10, activités à apprendre 0–5, exactement trois savoir-être, au moins un savoir-faire ou une activité. Catégories, recherche et étiquettes supprimables en FR/EN/DE. Savoir-être non éliminatoires ; aucun moteur de matching activé. Voir [contrat et limites](CANDIDATE_OPEN_SKILLS.md).

## 6 novembre 2026 — préparation d’un catalogue de 50 métiers

Eric demande une proposition de 50 métiers ou plus et la création des fichiers
depuis ESCO, sans données inventées. Préparation sur le sommet de livraison #154
vérifié à `d12374c` : 50 métiers distincts, sept existants conservés et 43 ajouts.
La liste détaillée et les sélections sont proposées à la relecture, pas validées
individuellement par Eric. Architecture des deux JSON et protections locales
conservées ; aucune correspondance ROME ou statistique de recrutement ajoutée.
Voir [la liste](SKILLS_CATALOGUE_50.md) et [les contrôles](SKILLS.md).

## 6 novembre 2026 — pilote commun de sélection des compétences

Eric choisit six métiers : nettoyage, espaces verts, service en restaurant,
sécurité, production agroalimentaire et vente de prêt-à-porter. Il demande un
parcours local employeur/candidat pour tester et valider avant push.
Le catalogue et les identifiants sont communs ; les questions et les réponses
restent distinctes par rôle. Les plafonds de cinq compétences et trois savoir-être
restent à éprouver en recette. Aucune publication, fusion ni production autorisée
par cette étape. Voir [les compétences](SKILLS.md).

## 6 novembre 2026 — évaluer Albert localement avant publication

Eric autorise une intégration locale limitée aux offres employeurs, une clé locale distincte et une évaluation des résultats. Il demande de tester personnellement le parcours avant tout push ou création de PR ; la recette jetable viendra après son accord. Les codes proposés restent issus des catalogues officiels, avec validation humaine. Voir [le contrat](ALBERT_IMPORT.md).

## 6 novembre 2026 — accroches publiques validées écran par écran

Eric valide successivement l’accueil, la page candidat et la page employeur.
Accueil : « L’emploi au-delà des frontières ». Candidat : « Travailler dans un
autre pays », puis « Décrivez votre projet professionnel. Match Europe identifie
les opportunités qui correspondent à votre profil. » Employeur : « Recruter dans
un autre pays », puis « Décrivez votre besoin de recrutement. Match Europe
identifie les profils qui correspondent à votre recherche. »

Signature commune : « Des correspondances pertinentes. Des mises en relation
consenties. » Les pages ne promettent ni catalogue d’offres consultable, ni
CVthèque, ni accompagnement individuel systématique. Les formulations existent
en FR/EN/DE ; une réserve visible rappelle que le matching et les mises en relation
ne sont pas encore disponibles. Enregistrer une offre ne lance pas de matching.
L’accord du candidat et de l’employeur reste nécessaire à la mise en relation.
Cette validation éditoriale n’autorise ni ouverture de droits, ni fusion, ni déploiement.

## 5 novembre 2026 — pratiques de réponse par compte employeur

Eric valide deux questions sur la réponse aux candidatures et le délai habituel.
Les réponses sont propres à chaque compte employeur : deux collègues du même
établissement peuvent avoir des pratiques différentes. Après une première
sauvegarde, afficher le récapitulatif et « Modifier mes réponses », avec champs
préremplis et annulation. Les futures échéances devront conserver la règle
applicable à la candidature, sans effet rétroactif des modifications.
Voir [le périmètre local et le stockage](EMPLOYER_RESPONSE_PRACTICE.md).

## 4 novembre 2026 — préparation du stockage candidat

Demande d'Eric : préparer, après la PR #127, la table enregistrant les réponses
saisies par le candidat. Modèle préparé : une fiche par compte candidat,
réponses structurées, email conservé dans le compte. Ce lot n'active pas la
collecte durable depuis le questionnaire. Le raccordement, la vérification
email et les modalités de conservation restent des étapes suivantes.
Voir [le contrat de stockage](CANDIDATE_PROFILE_STORAGE.md).

Initialisation : 16 octobre 2026. Sources : échange d’organisation avec Eric, AGENTS.md et documentation existante. Ce registre ne transforme pas une hypothèse en décision et n’atteste pas l’état des déploiements.

## 4 novembre 2026 — socle candidat et conservation des réponses

Eric autorise un travail par étapes : ajouter `candidate` à `User.Kind`, puis
créer le modèle des réponses. Il choisit des champs et tables dédiés pour
faciliter le futur matching, plutôt qu’un questionnaire conservé uniquement
dans un JSON versionné. La structure détaillée reste à implémenter.

Le parcours cible est ouvert sans connexion jusqu’à la fin du questionnaire :
le candidat indique alors son email, un compte est créé et un email lui est
envoyé. Cette décision remplace la proposition d’invitation préalable par un
conseiller ; elle n’ouvre pas les inscriptions employeurs ou conseillers.
La sauvegarde métier, la vérification email et le matching constituent des
étapes distinctes. Le premier lot technique ajoute seulement le rôle et sa
migration, sans collecte durable, compte public ni envoi supplémentaire.

## Choix validés et règles existantes

| Référence | Décision ou contrainte | Source |
| --- | --- | --- |
| D01 | Un projet commun EURES beta, quatre volets EMPLOYEURS, CANDIDATS, CONSEILLERS et ADMIN ; discussions distinctes par thème, avec TRANSVERSE pour les sujets communs. | Organisation acceptée par Eric le 16 octobre 2026. Configuration de l’application non vérifiée ici. |
| D02 | Vue d’ensemble et décisions dans `docs/` ; état du projet dans le `HANDOFF.md` existant ; consignes dans `AGENTS.md`. | Mise à jour demandée par Eric le 16 octobre 2026. |
| D03 | Maintenir l’historique Flask/Grist ; développer la cible Django/PostgreSQL/Bootstrap séparément. Aucune migration implicite. | AGENTS.md, section de transition ; README. |
| D04 | FR/EN/DE, sécurité, accessibilité, tests proportionnés et conformité EURES/ELA sont des exigences permanentes. | AGENTS.md. |
| D05 | Contrôler les droits côté serveur par rôle et par objet ; préserver les validations humaines, l’explicabilité et les accords requis. | AGENTS.md. |
| D06 | Code et ressources générales dans le dépôt public ; procédures et configuration FT dans le privé ; aucun secret dans les deux. Séparer EURES et FAGERH. | HANDOFF.md et AGENTS.md. |
| D07 | Une modification locale ou une PR n’autorise ni fusion, ni déploiement, ni écriture sur les données Grist réelles. | AGENTS.md. |
| D08 | Les essais du prototype utilisent des données fictives ; le prototype ne doit pas être déployé tel quel. | Documentation Match Europe et HANDOFF.md. |

## 26 octobre 2026 — vocabulaire des pages et API

À la demande de l’utilisateur, réserver « preview » aux recettes jetables.
Employer « page », « résumé » et « démonstration » pour l’interface et ses essais.
L’API commune utilise `/api/` ; l’option d’accès sur loopback est nommée
`ME_EMPLOYER_DEV_ACCESS`. Les contrôles d’accès ne changent pas.
Voir [les changements d’URL et de configuration](API_NAMING.md).

## Points restant à confirmer ou à concevoir

- Authentification, gestion et révocation des accès en production.
- Conservation, suppression et archivage des données ; validation des notices.
- Raccordement complet entre imports employeurs et parcours de matching/préqualification/conversation.
- Intégrations réelles restantes et conditions de passage en production.
- État effectif des environnements FT et Scalingo : vérifier séparément au moment d’une tâche qui les concerne.

Cette liste ne vaut ni autorisation de mise en œuvre ni choix définitif.

## Tenue du registre

Pour chaque nouveau choix important : indiquer la date, la décision, sa justification, les volets concernés et la source de validation. Une proposition reste marquée « à confirmer » tant qu’elle n’est pas validée. Si une décision est remplacée, conserver sa trace et pointer vers celle qui la remplace. AGENTS.md reste la référence pour les règles de travail ; ne pas les redéfinir silencieusement ici.

## 16 octobre 2026 — conservation du prototype dans un dépôt distinct

À la demande explicite de l’utilisateur : partager le premier prototype Django dans `eures-beta/match-europe`, sur une branche dédiée et une PR de conservation en brouillon. Commits regroupés par thème pour la lecture humaine. `main` ne doit recevoir aucun commit direct ; aucun merge ou déploiement. Le checkout historique et son travail non commité restent conservés.

## 23 octobre 2026 — préparation d’une démonstration partagée

L’utilisateur autorise le rebase et le push de la PR #2, ainsi que des adaptations
identifiables dans des commits séparés des sept commits initiaux. Il posera
lui-même le label de recette. Les règles initiales interdisant tout déploiement
décrivent le partage du 16 octobre ; cette autorisation ultérieure concerne
uniquement une recette fictive temporaire, pas une production ni une fusion.
## 21 octobre 2026 — vérification de l’import avant enregistrement

Décision employeurs validée par Eric dans la discussion : afficher le résultat de lecture et permettre sa correction avant de demander l’email ; porter la demande de lecture par le clic sur « Lire les documents » et sa notice, sans case d’accord supplémentaire. Mise en œuvre locale uniquement. Le texte de recette décrit le lecteur actuel (règles et OCR local) ; une future transmission à un prestataire ou utilisation d’IA générative devra avoir une information adaptée. Cette décision UX ne valide pas une base juridique de production et n’autorise aucune publication ni aucun déploiement.

## 22 octobre 2026 — collaboration RH par établissement

Eric valide un établissement partagé par plusieurs personnes habilitées. L’import
appartient à l’établissement et conserve son créateur. Les droits viennent de
l’appartenance active, sans correspondance automatique de nom, email ou domaine.
La simplification validée demande le nom uniquement au premier enregistrement,
utilise l’appartenance existante lorsqu’elle est unique et impose un choix explicite
s’il y en a plusieurs. La création d’un autre établissement n’est pas proposée
sur cet écran aux membres déjà rattachés et est refusée côté serveur.

Les invitations, l’identification officielle et le traitement des doublons restent
des lots séparés avant ouverture réelle. Les homonymes peuvent exister mais ne
partagent aucun droit. `EmployerCompany` reste le nom technique du modèle ; il
représente ici l’établissement. Aucun identifiant officiel obligatoire ni changement
du matching fictif dans cette PR. Voir [lot 2](EMPLOYER_COMPANY_OWNERSHIP.md).

## 22 octobre 2026 — accès employeur indépendant du dépôt

Périmètre demandé par Eric : connexion sans offre, accueil avec établissements
autorisés et ajout depuis la session valide. Le contact conseiller est distinct
de l'identité connectée. Réutiliser les appartenances actives de la PR #19 ;
aucun droit par nom, email de contact ou domaine. Liste des offres, modification,
invitations, recrutement et identification officielle exclus de ce lot.

## 22 octobre 2026 — lot 3 et verrouillage au démarrage de la recherche

Eric précise que l’offre reste modifiable jusqu’au démarrage effectif de la
recherche de candidats, plutôt que jusqu’à sa transmission. Après démarrage :
consultation et duplication en nouveau brouillon, sans modifier l’original.
Le futur bouton « Lancer ma recherche de candidats » appartient au lot suivant ;
verrouillage seulement après confirmation serveur du démarrage. Clôture séparée.
Le lot 3 couvre liste, consultation, modification avant recherche et duplication,
avec les habilitations par établissement existantes. Aucun démarrage déduit d’un
nom, d’un envoi de préparation ou d’une validation.
Voir [lot 3](EMPLOYER_OFFER_WORKSPACE.md).

## 22 octobre 2026 — lot 4A employeur

Eric valide un premier sous-lot de lancement simulé comprenant recherche,
qualification et contact. Les modifications sont temporairement suspendues tant
que le démarrage est en cours ou incertain ; seul un démarrage confirmé renseigne
la date de verrouillage définitif. Aucun contact réel autorisé. Clôture, archivage,
effets sur les dossiers en cours et réouverture restent des décisions à prendre.
Voir [périmètre du lot 4A](EMPLOYER_SEARCH_LAUNCH.md).

## 28 octobre 2026 — reprise du volet candidat

Eric valide la reprise de l’accueil candidat du 26 octobre sur le main actuel,
avec l’identité visuelle et les trois entrées CV/LinkedIn/saisie manuelle déjà
validées. L’ancienne dépendance à la PR #15 n’est pas reprise. Ce lot conserve
les interactions simulées ; il ne valide pas encore le parcours de profil,
l’authentification candidat ni une collecte réelle de données.

## 29 octobre 2026 — catalogue local, reprise sur le train

Eric confirme de préserver les travaux candidat hors de cette reprise et
d’adapter le catalogue et l’intégration employeur à l’architecture du sommet du
train (#74 vérifiée au départ). Catalogue partagé indépendant, puis intégration
employeur dans une branche dépendante. Pas de générateurs ni de dossier métier
`journeys` réintroduits. Les nouvelles PR de livraison cibleront le sommet courant
du train unique, les essais incertains restant hors train. Aucune fusion ou
mise en production autorisée.

## 30 octobre 2026 — information sur le dépôt employeur

Eric demande de présenter le dépôt de besoins réels comme enregistré, en distinguant
le rapprochement avec les candidats, encore indisponible et annoncé prochainement
sans date garantie. Le bandeau commun aux pages employeur affiche le statut de
développement et son adresse professionnelle de retour. Le logo Match Europe
existant est repris, sans modifier les logos officiels partenaires.
Cette décision éditoriale ne vérifie pas le stockage distant, ne transforme pas
une recette jetable en service permanent. Eric autorise ensuite la création
d’une PR au sommet de la pile et une recette jetable, sans fusion ni production.

## 2 novembre 2026 — contenu du journal public

Eric demande de conserver l’historique et d’ajouter la mobilisation ADEM, FOREM
et France Travail Grand Est (un conseiller à un tiers temps par structure).
Distinction éditoriale retenue : engagement à partir du 4 septembre, arrivée des
collègues dans les travaux début octobre. La priorité a été leur accueil et leur
prise en main du projet ; aucune acquisition n’a été menée pendant cette phase.
Le bilan chiffré au 2 novembre est retiré à sa demande. Publication GitHub après
validation du rendu, au sommet de la pile ; aucune fusion ni mise en production.

## 2 novembre 2026 — identité Django unique

Choix validé par dejafait : hériter d’AbstractUser comme Les Emplois, avec le
champ `kind`, deux valeurs exclusives conseiller/employeur, e-mail unique sans
distinction de casse et rôle obligatoire fixé à la création. Aucun Profile.
EmployerIdentity est remplacé par ce compte commun ; les habilitations aux
établissements restent distinctes. Voir [les migrations et limites](USER_MODEL.md).

## 2 novembre 2026 — connexion publique sans mot de passe

Demande de dejafait : bouton commun, comptes existants uniquement, lien magique et
session de 30 jours d’inactivité. La PR dédiée utilise django-sesame, des liens
de 15 minutes à usage unique et une confirmation POST. L’envoi SMTP reste
désactivé en attente du raccordement e-mail ; la recette est visuelle à ce stade.
Inscriptions fermées, invitations non implémentées. Voir [le fonctionnement
et ses limites](MAGIC_LOGIN.md).


## 2 novembre 2026 — proposition locale candidat

Eric demande la version locale du parcours proposé : CV facultatif, projet explicite, parcours vérifiable, conditions puis relecture. Utiliser des noms métier et abandonner les identifiants historiques dans les nouveaux champs. Cette autorisation couvre la recette locale, pas une collecte réelle, publication ou sauvegarde durable. Le détail des questions reste une proposition à essayer. Voir [recette](CANDIDATE_JOURNEY.md).


### Ajustement du 2 novembre — choix guidés candidat

Eric demande de reprendre le fonctionnement employeur : privilégier les choix guidés et intégrer la recherche ESCO/ROME. Les deux catalogues restent indépendants ; les réponses candidat portent sur les souhaits ou éléments déclarés, sans déduction depuis le CV. La saisie libre complète les choix et conserve les descriptions de parcours.


## 2 novembre 2026 — abandon du CV dans le nouveau parcours candidat

Eric demande de s’inspirer du questionnaire historique FT, de garder la recherche métier ESCO/ROME et de retirer import CV, expériences professionnelles, formations/diplômes et compétences. La version locale devient un questionnaire de projet en quatre étapes : projet, mobilité/langues, conditions, relecture. Les décisions antérieures sur le préremplissage CV sont abandonnées pour ce parcours. Aucune modification du questionnaire Flask ni collecte réelle autorisée.


### Langues candidat — réutilisation du module employeur

Eric demande le module employeur pour les langues candidat. Réutiliser la recherche et les niveaux expliqués, en adaptant les formulations au niveau déclaré de la personne. Aucune déduction depuis un métier, CV ou langue maternelle.


### Conditions candidat et grille horaire

Eric demande des précochages et la détection des incohérences. Reprise locale : propositions limitées aux horaires explicitement présents, corrections manuelles prioritaires ; absence de créneau interprétée comme exclusion uniquement après confirmation explicite des seules disponibilités. Aucun souhait de travail physique ou autre condition non temporelle déduit.
# E-mails réels

Tous les e-mails Django passent par un backend SMTP exigeant production déclarée
et activation explicite. Local et recettes ne doivent jamais être déclarés
production. Secrets exclusivement dans la configuration privée ; tests simulés.
## Renommage des trois modèles employeur — 3 novembre 2026

Choix validé par dejafait : `EmployerCompany` devient `Company`,
`EmployerMembership` devient `CompanyMembership`, `EmployerImport` devient
`JobOffer`. Les six autres modèles applicatifs ne sont pas renommés. Conserver
les tables, données, relations, identifiants de types de contenu et de droits.
Pas de changement de champs ni de comportement métier dans ce lot.

## 9 novembre 2026 — questionnaire candidat sans compte préalable

À la demande de dejafait, abandon de la PR #164 : entrée anonyme et email à la
fin. Les brouillons temporaires utilisent les sessions Django existantes, sans
modèle CandidateRegistration. Vérification obligatoire avant création du compte
et du profil ; un profil existant n’est remplacé qu’après comparaison et décision
explicite du propriétaire connecté. Les comptes d’autres rôles ne sont jamais
convertis. Voir [le parcours et la migration](CANDIDATE_EMAIL_REGISTRATION.md).
## 7 novembre 2026 — présentation du projet candidat ouvert

Eric demande les secteurs d’activité en première lecture, à déplier pour voir les compétences, et des savoir-être plus compréhensibles. Les volets natifs par secteur remplacent le volet général des deux listes techniques. Les savoir-être ont un intitulé simple, un exemple concret et trois groupes de lecture ; les URI ESCO et les règles de saisie ne changent pas. Les formulations sont des aides éditoriales FR/EN/DE, pas de nouvelles compétences ou critères de matching.

## Notifications candidat sans distinction d’environnement

Le Push appartient au parcours métier, pas à l’outil de comptes fictifs. Un
candidat ordinaire peut s’abonner dans chaque environnement. Le conseiller peut
valider sans abonnement ; l’envoi éventuel intervient après le commit.
