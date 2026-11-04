# Stockage des réponses candidat

Ce lot prépare le stockage durable après le rôle candidat de la PR #127.
Le questionnaire de démonstration conserve son fonctionnement en session :
aucune vue, API publique, création de compte ou vérification d'email n'est ajoutée.

## Une fiche par compte candidat

`candidates.CandidateProfile`, table `candidates_candidateprofile`, possède un
UUID, une relation unique et obligatoire vers `users.User`, et des dates de
création/modification. Le compte doit avoir le rôle `candidate` : contrôle
applicatif et déclencheur PostgreSQL, y compris lors d'une écriture contournant
`save()`. Le rôle du compte reste immuable selon le socle existant.

La fiche contient des réponses complètes validées, pas un brouillon anonyme.
L'email reste exclusivement dans `users_user`. Le nom d'affichage appartient à
la fiche ; il ne constitue pas une identité vérifiée. La langue choisie est
limitée à FR/EN/DE. L'existence d'une fiche n'atteste jamais une vérification
d'email, un consentement ou une validation par un conseiller.

| Groupe | Colonnes et représentation |
| --- | --- |
| Projet | `desired_occupations`, `occupation_references`, `desired_countries`, `desired_locations` |
| Mobilité | `mobility`, `commute_time`, `transport_modes`, `transport_details` |
| Langues/permis | `language_skills`, `licences_held`, `licence_details` |
| Disponibilité | `availability`, `available_from` (date facultative) |
| Contrats | `contract_types`, `contract_details`, `working_time` |
| Horaires | `schedule_preference`, `schedule_strict`, sept colonnes `schedule_<jour>` |
| Conditions | `working_conditions`, `condition_details` |
| Salaire | `salary_preference`, `salary_amount` (décimal facultatif), `salary_currency`, `salary_period`, `salary_basis` |

Les valeurs simples sont des colonnes texte, booléennes, date ou décimales.
Les listes de choix et les langues structurées utilisent des colonnes JSONB,
pas une copie opaque de toute la session. ESCO et ROME gardent leurs références
distinctes (`esco:…`, `rome:…`) contrôlées dans le catalogue local courant.
Les libellés localisés sont résolus à l'affichage ; pas d'équivalence inventée.
Le lot ne constitue pas un historique des versions du catalogue.

## Validation et droits

`save()` appelle `full_clean()` et réutilise les validations serveur des trois
étapes métier du questionnaire : choix autorisés, langues/niveaux, cohérence
des horaires exclusifs, disponibilité datée, montant/devise/période/brut-net.
Les champs conditionnels inactifs sont remis à vide. Les écritures partielles
`save(update_fields=…)` sont refusées pour préserver cette normalisation.
Les contrôles applicatifs ne sont pas exécutés par les opérations ORM de masse
ou SQL direct ; ces voies ne doivent pas servir à enregistrer des réponses
externes. Un futur service d'enregistrement devra valider explicitement les
entrées et les droits par compte avant l'écriture.

La base impose aussi l'unicité du compte, la clé étrangère, la langue et le
montant non négatif. Elle ne remplace pas la validation métier du questionnaire.
Les jetons de session, recherches de métiers, états de précochage, fichiers et
case de confirmation fictive ne deviennent pas des données métier durables.

L'administration est explicitement en lecture seule et limitée à l'UUID et aux
dates, pour les seuls superutilisateurs actifs habilités par le socle. Aucun
détail des réponses ni lien vers une fiche personnelle n'y est exposé. Aucun
nouvel accès employeur ou conseiller n'est créé.

## Migration et conservation

`candidates.0001_initial` dépend de `users.0005_candidate_kind` et ajoute une
table vide et son contrôle de rôle. Aucun compte ni réponse existants ne sont
modifiés ou repris depuis les sessions. La suppression d'un compte via l'ORM
supprime sa fiche liée (`CASCADE`). Aucun nouveau parcours de suppression
n'est exposé. La migration inverse supprime la table et ses réponses : après
collecte réelle, elle exige une décision explicite et une sauvegarde adaptée.

Aucune durée de conservation ou purge automatique n'est définie par ce lot.
La notice, la durée de conservation, la vérification email et le moment exact
de création atomique compte/fiche restent à définir avant le raccordement réel.
La confirmation de démonstration n'est pas un consentement à une collecte réelle.
Ni matching, ni email, ni transmission à un tiers ne sont déclenchés.

## Vérifications locales

- `make candidate-test` : réponses, contraintes, administration et migration
  aller/retour sur PostgreSQL avec données fictives.
- `make test` : suite complète et interactions avec les autres domaines.
- `make check` : configuration Django et absence de migrations manquantes.
- `make migrate` : application à la base sélectionnée par le `.env` local.
- `make format-check`, `make translations-check`, `make translations-compile`.

La base locale de ce worktree est distincte de celles des autres travaux.
Aucune exécution de migration de production n'est autorisée par ce document.
