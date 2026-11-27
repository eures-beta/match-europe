# Comprendre les données fictives

Ce paquet prépare des exemples liés dans les bases locales et recettes autorisées.
Les données sont écrites en **Python**, puis créées en PostgreSQL par la commande
de peuplement. Ce ne sont pas des fichiers JSON de fixtures Django.

Les nombres ci-dessous décrivent une base fraîche, avant toute manipulation.
Ils comptent les lignes **au total dans la base**, jamais « par compte » sauf
mention explicite. Une relance conserve les essais existants.

## Comptes et profils

La PR d’enrichissement conserve neuf comptes : un conseiller, un administrateur,
deux employeurs et cinq candidats. Deux candidats sont proposés dans le sélecteur :
profil complet A et profil incomplet B. Les trois autres illustrent une date de
disponibilité incompatible, des horaires incompatibles et un permis absent.

La [PR de simplification des comptes](https://github.com/eures-beta/match-europe/pull/271)
vient ensuite : elle conserve ces cinq candidats mais réunit les deux employeurs
en **un seul compte employeur**, soit huit comptes au total sur une base fraîche.
Elle préserve les seize offres et leurs rapprochements. Les deux candidats du
sélecteur ne sont pas fusionnés.

Un `EmployerProfile` contient les pratiques de réponse d’un compte employeur ;
ce n’est pas une entreprise supplémentaire. Il y en a deux avant la simplification,
un après celle-ci sur une base fraîche.

## Pourquoi seize offres ? Quels métiers ?

Il y avait trois offres. Treize variantes ont été ajoutées pour montrer plusieurs
étapes du recrutement simultanément, sans devoir transformer un même dossier pour
passer de l’une à l’autre. **Ce ne sont pas seize métiers différents.**

| Origine | Nombre | Métier / fonction |
| --- | ---: | --- |
| Brouillon historique « Cleaner » | 1 | Nettoyage, sans métier ESCO structuré |
| Brouillon historique « Baker » | 1 | Boulangerie, sans métier ESCO structuré |
| Offre structurée historique « entretien » | 1 | Aide ménager à domicile / aide ménagère à domicile, ESCO |
| Variantes de parcours de cette offre | 13 | Même métier ESCO et mêmes exigences de départ |

Il y a donc quinze offres autour du nettoyage et une de boulangerie. Les treize
variantes changent le titre et l’étape du parcours, pas le métier ni les exigences.
Les deux brouillons historiques n’ont aucun rapprochement.

Le cache de suggestions de compétences contient aussi deux références ESCO :
« aide ménager à domicile / aide ménagère à domicile » et « agent d’entretien
d’immeubles / agente d’entretien d’immeubles ». Cette seconde référence sert
seulement à illustrer les suggestions ; aucune des seize offres ne la cible.
Les profils candidats ont un projet ouvert et des compétences de nettoyage :
ils ne représentent pas cinq métiers différents.

Avant la simplification : onze offres pour l’employeur principal et cinq pour
le second. Après la PR271 : les seize offres appartiennent à l’employeur unique.

## Rapprochements, évaluations, décisions et revues

Un **rapprochement** relie exactement un profil candidat à une offre. Une
**évaluation** est un calcul enregistré pour ce rapprochement ; plusieurs calculs
successifs sont possibles dans l’application, mais le jeu initial en crée un seul.

- L’offre structurée historique est rapprochée des cinq candidats : **5 rapprochements
  et 5 évaluations**. C’est ce que signifiait « cinq chacun ».
- Chacune des treize nouvelles offres est rapprochée d’un seul des deux candidats
  du sélecteur : **13 rapprochements et 13 évaluations supplémentaires**.
- Total : **18 rapprochements et 18 évaluations**, soit 36 lignes dans deux tables.
  Ce ne sont pas 36 rapprochements.

Répartition par candidat : A a dix rapprochements, B en a cinq, et les trois autres
en ont un chacun : **10 + 5 + 1 + 1 + 1 = 18**.

Une **décision** est un choix du conseiller sur un rapprochement et son évaluation.
Le jeu contient quatorze décisions : treize « retenu » et une « refusé ». Les quatre
autres rapprochements attendent encore une décision. Ces quatorze décisions sont
réparties sur quatorze rapprochements différents, pas répétées quatorze fois sur
chacun d’eux.

Une **revue** permet au candidat d’examiner une offre retenue pour lui. Chacun des
treize rapprochements retenus a une revue : treize revues au total, huit pour A et
cinq pour B. Le rapprochement refusé et les quatre encore en attente n’en ont pas.

## Les treize variantes ajoutées

A désigne le candidat au profil complet, B le candidat au profil incomplet.
Une ligne du tableau représente une offre supplémentaire et un rapprochement.

| Scénario | Candidat | Revue / conversation préparée |
| --- | --- | --- |
| Rapprochement refusé | A | Aucune revue |
| Revue close | A | Revue close par le conseiller |
| Réponses à examiner | A | Revue prête |
| Dossier pris en charge | B | Revue prise en charge |
| Précision demandée | A | Revue en attente d’un complément |
| Invitation à converser | A | Conversation demandée |
| Conversation acceptée | B | Conversation acceptée, pas encore ouverte |
| Conversation ouverte | A | Conversation ouverte, trois messages |
| Échange en cours | B | Conversation ouverte, trois messages |
| Invitation refusée | B | Conversation refusée |
| Préférences à revoir 1 | A | Horaires et salaire refusés pour cette offre |
| Préférences à revoir 2 | A | Même refus sur une deuxième offre |
| Préférences à revoir 3 | A | Même refus sur une troisième offre |

Les trois derniers cas montrent une répétition sur trois offres distinctes,
nécessaire pour déclencher les deux suggestions de réexamen du profil.

## Pourquoi 169 réponses et 27 événements ?

Chaque revue contient ici treize réponses : métier, employeur, horaires, date de
début, condition de travail, mobilité, contrat, salaire, permis, trois compétences
et langue. Cela donne **13 revues × 13 réponses = 169 réponses enregistrées**.
Ce n’est pas un questionnaire de 169 questions posé à chaque candidat. A en a 104
(8 × 13), B en a 65 (5 × 13). Six réponses sont « non » : horaires et salaire sur
les trois offres « Préférences à revoir ». Les 163 autres sont « oui ».

Les **événements de revue** sont l’historique des actions, pas les réponses aux
questions ni les messages d’une conversation. Les vingt-sept lignes correspondent à :

| Action | Nombre |
| --- | ---: |
| Remise des réponses et du choix de partage | 12 |
| Prise en charge par le conseiller | 8 |
| Validation par le conseiller | 5 |
| Demande de précision | 1 |
| Clôture / refus par le conseiller | 1 |
| **Total** | **27** |

La revue historique de B a ses réponses mais attend encore le choix de partage ;
elle ne produit donc pas encore d’événement de remise. Les douze nouvelles revues
ont ce choix. Au départ, les treize revues sont réparties en une en attente,
quatre prêtes, une prise en charge, une à préciser, cinq validées et une close.

## Partage du profil, conversations et messages

Les **douze lignes de partage ne sont pas douze autorisations positives** : huit
contiennent un accord et quatre un refus (revue close et trois cas de préférences).
La treizième revue n’a pas encore de choix. Le modèle peut conserver plusieurs
choix successifs ; le jeu initial n’en crée qu’un par revue concernée.

Cinq des revues validées ont chacune une conversation : une demandée, une acceptée,
une refusée et deux ouvertes. Seules les deux ouvertes ont des messages : trois
chacune, soit **six messages au total**. Une conversation ouverte appartient à A,
l’autre à B. Après simplification des comptes, le même employeur participe aux deux.

## Autres données et limites

Une disponibilité fictive du conseiller est enregistrée pour le 23 novembre 2026.
Le peuplement ne remplace jamais une disponibilité déjà modifiée dans le planning.

Les cinq candidats ont un accompagnement. Onze offres ont un accompagnement dans
la PR270 ; les seize en ont un après la simplification des employeurs dans la PR271.
Trois invitations illustrent attente, expiration et acceptation. Deux suggestions
de préférences et deux suggestions de compétences complètent les interfaces.

Les modèles techniques ont également des exemples : abonnements Push `.invalid`
non livrables, sessions de confirmation sans authentification, compteurs anti-abus
expirés et journal d’initialisation explicitement fictif. Aucun envoi réel n’a lieu.
Voir [les compteurs et les limites détaillées](../../../docs/PREVIEW_DATASET.md).

## Où lire le code et préparer la base ?

- [scenarios.py](scenarios.py) — Offres, rapprochements, revues, conversations et accompagnements liés.
- [followups.py](followups.py) — Trois suivis fictifs : échéance passée, échéance future et clôture motivée, avec une conclusion sans embauche et son événement ; aucun envoi ni remplacement d’un suivi existant.
- [supporting.py](supporting.py) — Invitations, profils employeurs et exemples techniques fictifs.
- [report.py](report.py) — Compteurs des modèles actifs, sans modification.
- [__init__.py](__init__.py) — Déclare le paquet.

Les [deux brouillons historiques](../../employers/test_data.py) et
l’[offre structurée avec les cinq candidats](../../matching/management/commands/seed_matching_trial.py)
sont définis séparément. La [commande principale](../management/commands/seed_test_accounts.py)
réunit ces sources et ce paquet.

```bash
make test-accounts-seed
make test-accounts-seed SEED_ARGS=--report
```

Voir [la couverture et les limites](../../../docs/PREVIEW_DATASET.md).

[Remonter au domaine utilisateurs](../).

Une demande employeur en attente est liée à l’accord candidat du scénario
« Conversation acceptée ». Sa création est idempotente et ne modifie jamais
les réponses ou décisions d’une demande déjà explorée.
