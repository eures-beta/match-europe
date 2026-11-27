# Rapprochement, mise en relation et accompagnement

Trois applications Django séparent les responsabilités auparavant réunies dans
`matching`. Les parcours, URL, réponses, accords et décisions restent identiques.
Les interfaces HTTP demeurent dans [www/](../eures_beta/www/).

| Domaine | Modèles | Responsabilité |
| --- | --- | --- |
| [matching](../eures_beta/matching/) | CandidateOfferMatch, MatchEvaluation, MatchDecision, MatchEvent | Calcul explicable, présélection et journal du matching |
| [introductions](../eures_beta/introductions/) | CandidateOfferReview, CandidateOfferReviewAnswer, CandidateProfileSharing, EmployerCandidateReview, CandidateOfferConversation, CandidateOfferConversationMessage | Questions, réponses, accords et conversation |
| [followup](../eures_beta/followup/) | JobOfferSupport, CandidateSupport, MatchFollowup, MatchConclusion | Accompagnement, prochaine action, relance et issue vérifiée |

`introductions` utilise le rapprochement ; `followup` peut lire les deux domaines.
Le calcul ne dépend pas des étapes suivantes. La synthèse du cycle de vie reste
dans `followup/match_lifecycle.py` ; les accords ne sont pas dupliqués dans le suivi.
Les accompagnements candidat/offre existent indépendamment d’un rapprochement.
Une conversation appartient à une mise en relation, sans quatrième application.

## Données et migration

Aucun nouveau modèle métier ni champ n’est ajouté : treize modèles changent
d’application, les trois modèles de calcul/décision restent dans `matching`.
Les migrations historiques sont conservées. Les nouveaux états Django prennent
en charge les tables existantes, puis celles-ci sont renommées en place avec
leurs contraintes, index, séquences, fonctions et déclencheurs PostgreSQL.
Il n’y a ni copie, ni suppression de lignes, ni remise à zéro d’identifiants.

Les ContentTypes changent de label en conservant leurs identifiants : permissions,
attributions aux comptes/groupes et entrées du journal admin restent reliées.
Un doublon de ContentType provoque un arrêt explicite plutôt qu’une fusion de droits.
Les trois cibles d’application terminent le transfert avant `post_migrate`.
L’administration reste en consultation et présente les trois groupes de modèles.
Les anciennes adresses de modèles de l’admin changent avec leur application ;
les URL publiques des parcours restent inchangées.

Le retour arrière rétablit les anciennes applications et tables, sans supprimer
les réponses et événements créés entre-temps. Comme tout renommage DDL, la
migration prend des verrous ; elle nécessite une livraison contrôlée.

## Vérification

```bash
make check
make test TESTS=tests.matching.test_domain_extraction
make test
make e2e-test
```

Les tests peuplent les treize tables et contrôlent l’aller-retour, les OID des
tables/séquences/déclencheurs/fonctions, les relations, JSON, permissions et journaux.
Les tests de parcours couvrent aussi les refus d’accès. Le [journal commun](MATCH_EVENTS.md) rassemble ensuite les événements de revue,
de suivi et de conclusion sans changer les règles du recrutement.

[Architecture web](ARCHITECTURE_WEB.md) · [Noms du schéma](MODEL_NAMING.md) · [Documentation](.)
