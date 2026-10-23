# EURES beta / Match Europe — vue d’ensemble

Référence commune créée le 16 octobre 2026 à partir des README et de HANDOFF.md. Ce document décrit le cadre produit ; il ne constitue pas une vérification de production.

## Objectif et périmètre

Organiser les parcours employeur, candidat, conseiller et administrateur pour préparer une mise en relation explicable, avec validation humaine et accords des participants.

Deux implémentations coexistent :

- **EURES beta historique** : Flask/Grist, formulaires, statistiques et administration/suivi. Voir le dépôt historique [eures-beta/eures-beta](https://github.com/eures-beta/eures-beta).
- **Match Europe local** : Django/PostgreSQL/Bootstrap dans `match_europe/`, pour essayer les nouveaux parcours. Voir [documentation locale](../match_europe/README.md). Ce prototype n’est pas prêt pour la production.

## Les quatre volets

| Volet | Responsabilité et parcours | Liens avec les autres volets |
| --- | --- | --- |
| EMPLOYEURS | Préparer/importer une offre, vérifier ses informations et son contact, définir les questions, examiner les réponses et accepter la présentation. | Le conseiller suit les offres attribuées ; le candidat répond ; les accords ouvrent la conversation. |
| CANDIDATS | Préparer un profil, préciser souhaits et mobilité, manifester un intérêt, répondre aux questions et accepter la présentation. | Le conseiller accompagne la qualification ; l’employeur reçoit les réponses selon les droits. |
| CONSEILLERS | Examiner les propositions, demander des précisions, accompagner la mise en relation et participer à la conversation. | Accès limité aux objets et participants autorisés ; suivi des imports attribués par l’administration. |
| ADMIN | Superviser les accès et activités autorisées, attribuer ou retirer un conseiller sur un import. | Droits spécifiques à vérifier par objet ; le rôle admin ne donne pas par défaut accès à toutes les conversations. |

Ces volets sont des domaines fonctionnels et des préfixes de discussions, pas quatre projets indépendants ni une nouvelle organisation imposée au code.

## Parcours et limites à distinguer

- Le scénario de démonstration relie offre, candidat, préqualification, double accord et conversation à trois avec des données fictives.
- Le parcours employeur d’import possède ses propres brouillons et objets `EmployerImport`. Leur affichage aux conseillers/admins ne les convertit pas en `Offer` et ne lance pas le matching.
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
