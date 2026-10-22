# EURES beta / Match Europe — décisions communes

Initialisation : 16 octobre 2026. Sources : échange d’organisation avec Eric, AGENTS.md et documentation existante. Ce registre ne transforme pas une hypothèse en décision et n’atteste pas l’état des déploiements.

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

## Points à confirmer ou à concevoir

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
