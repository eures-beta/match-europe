# Noms des modèles et du schéma PostgreSQL

Cette convention concerne le socle et les trois parcours métier. Les classes
restent dans le `models.py` de leur application ; les fichiers métier dédiés
suivent le concept actuel (`offer_review_services.py`, `profile.py`).

## Tables harmonisées

| Modèle | Ancienne table | Table actuelle après migration |
| --- | --- | --- |
| JobOffer | journeys_employerimport | employers_joboffer |
| CandidateOfferMatch | matching_matchpair | matching_candidateoffermatch |
| MatchEvaluation | matching_evaluation | matching_matchevaluation |
| MatchDecision | matching_decision | matching_matchdecision |
| CandidateOfferReview | matching_confirmationrequest | matching_candidateofferreview |
| CandidateOfferReviewAnswer | matching_confirmationanswer | matching_candidateofferreviewanswer |
| CandidateProfileSharing | matching_transmissionagreement | matching_candidateprofilesharing |
| EmployerCandidateReview | matching_employerofferconsent | matching_employercandidatereview |
| Invitation | users_invitation | invitations_invitation |
| OccupationSkillSuggestion | occupations_occupationskillsuggestion | skills_occupationskillsuggestion |

## Relations et objets associés

Les évaluations, décisions et revues référencent `match`.
Les réponses et partages référencent `review` ; les
`CandidateOfferConversation` gardent leur relation `offer_review` introduite
dans la PR précédente, avec les `CandidateOfferConversationMessage` associés.
Les accès inverses deviennent `job_offers`, `owned_job_offers`,
`advised_job_offers` et `profile_sharings`.

Les contraintes déclarées portent le préfixe de la table. Pour les index
déclarés, Django limite normalement les noms à 30 caractères : le préfixe
est alors raccourci et identifié par une empreinte du nom actuel de la table
(`config.model_naming.schema_prefix`), sans conserver un ancien nom. Les index, clés
primaires, clés étrangères, contraintes automatiques, séquences, fonctions et
triggers PostgreSQL sont également renommés. Les noms automatiques dépassant
63 caractères sont raccourcis avec une empreinte déterministe ; aucune
collision ne se résout par une suppression silencieuse.
Les contraintes NOT NULL nommées de PostgreSQL 18 sont lues directement dans
`pg_constraint`, car Django ne les expose pas dans son introspection habituelle.

Les contenus métier, routes HTTP, droits et parcours restent identiques. Les
chaînes de version des empreintes métier restent stables : les modifier
invaliderait des réponses existantes. Les anciennes migrations et fixtures
historiques gardent leurs noms pour permettre la reprise des schémas déployés.
La commande `migrate` garde aussi sa détection de l’ancienne table avant la
transition utilisateurs : elle examine précisément une base historique.

## Migration et retour arrière

Six migrations natives changent les noms de tables, champs, relations et
contraintes déclarées. La migration matching suivante normalise les noms des
objets PostgreSQL en place, y compris les objets des tables User M2M. Aucun
modèle ni champ métier n'est supprimé ou recréé. Les changements de contraintes
déclarées remplacent uniquement ces contraintes dans la transaction.
Dans matching, `0010_harmonize_model_names` et `0011_harmonize_database_objects`
suivent `0009_candidate_offer_conversation_names`, sans modifier cette migration
ni les migrations déjà intégrées dans `main`.

Les renommages conservent les OID des tables et séquences, leurs lignes, leurs
valeurs et leurs dépendances. Ils prennent néanmoins des verrous DDL : prévoir
une fenêtre de déploiement adaptée à une base active. Le retour arrière restaure
les anciens noms de tables et colonnes et des noms cohérents d'objets associés ;
il ne prétend pas restaurer chaque ancien suffixe aléatoire généré par Django.

## Vérification continue

`make check` refuse les tables ou noms déclarés incohérents et les anciennes
relations connues. `make test` couvre les contrats statiques, l'aller-retour du
schéma avec données liées, les identifiants et séquences, les droits, les
contraintes d'unicité, les protections de rôle et les parcours applicatifs.
Les tests de migrations utilisent les modèles historiques du graphe ciblé,
jamais la commande de peuplement fondée sur l'ORM actuel.

[Retour au dossier de documentation](.)

## Relations utilisateur à rôle explicite

`JobOffer.employer` désigne le propriétaire employeur, même lorsqu’un conseiller
dépose l’offre ; `JobOffer.adviser` conserve le conseiller. L’accès inverse est
`owned_job_offers`. Ce n’est pas une attribution automatique au créateur connecté.
`CandidateOfferReview.assigned_to_adviser`, les deux suivis
`updated_by_adviser` et `Invitation.sender_adviser` n’acceptent que des conseillers.
Les champs `actor` des événements et `author` des messages restent multirôles.
Le destinataire d’une invitation reste multirôle, déterminé par `recipient_kind`.

Les contrôles du modèle et les triggers PostgreSQL protègent aussi les écritures
ORM directes. Un compte désactivé garde son historique ; les services exigent un
compte actif pour agir. Les migrations refusent les anciennes attributions de
rôle incorrect au lieu de les réaffecter. Renommage des colonnes, index et FK en
place, sans suppression des lignes ; retour arrière testé sur données non vides.
