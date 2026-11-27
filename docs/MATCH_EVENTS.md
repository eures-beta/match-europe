# Journal du matching

`matching.MatchEvent` rassemble les événements de revue candidat, de suivi et
de conclusion. Chaque ligne appartient directement à un `CandidateOfferMatch`,
sans relation redondante vers une revue, un plan ou une conclusion.

## Catégories et données

`kind` distingue `review`, `followup` et `conclusion`. Les actions autorisées
sont contrôlées en base. Les versions des revues et conclusions restent deux
compteurs indépendants : l’unicité porte sur matching, catégorie et version.
Les événements de suivi n’avaient pas de version et gardent une version nulle.
Les auteurs de suivi sont des conseillers ; une déclaration d’embauche vient
d’un employeur et sa confirmation d’un conseiller, contrôlés aussi par PostgreSQL.

Les notes internes, messages publics, messages de relance, instantanés JSON,
destinataires, résultats du transport, dates et motifs restent distincts.
`review.events`, `plan.events` et `conclusion.events` sont des requêtes filtrées
du journal commun, sans nouvelles tables ni clés étrangères. La fiche conseiller
lit directement le journal du matching. Les messages de conversation et les
réponses candidat restent leurs propres objets métier.

## Confidentialité

Le journal complet est réservé aux conseillers. Le candidat continue de lire
uniquement les messages publics de la catégorie revue dans sa propre revue ;
un message de relance ou un motif de clôture ne devient jamais public parce
qu’il figure dans la même table. L’admin reste en consultation des métadonnées.
La notification après commit conserve la catégorie revue, son destinataire et
son résultat d’envoi ; aucune nouvelle notification automatique n’est créée.

## Migration et retour arrière

La migration copie les trois journaux avant de supprimer leurs tables. Les
identifiants des matching, revues, plans et conclusions restent inchangés.
Deux anciens journaux peuvent avoir le même identifiant : le nouvel identifiant
global est donc distinct, tandis que `kind` et `source_id` conservent l’identité
d’origine. Auteurs, dates exactes et tous les champs de chaque source sont copiés.

Le retour arrière restitue les identifiants d’origine et attribue des identifiants
libres aux événements créés depuis la fusion. Il restaure aussi les séquences et
les contrôles d’auteur. Si un objet métier nécessaire a été supprimé entre-temps,
le retour arrière refuse de perdre son historique et annule la transaction.

Vérification : `make test TESTS='tests.matching.test_match_events tests.matching.test_match_event_migration'`,
puis tests des domaines `tests.introductions` et `tests.followup`.

[Domaines](MATCHING_DOMAINS.md) · [Ligne de vie](MATCH_FOLLOWUP.md)
