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
