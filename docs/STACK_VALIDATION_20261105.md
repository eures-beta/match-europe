# Validation de la pile candidat / employeur — 5 novembre 2026

## Périmètre

Base vérifiée : `main` à `070038d`, PR #127 (rôle candidat), #128 (stockage),
puis #129 (parcours), sommet `62e4022`. Correctifs isolés sur
`codex/validate-candidate-employer-stack`, sans modification des branches des
autres contributeurs. Aucune fusion ni opération de production.

## Résultats

- Avant correction, `make test` sur #129 : **386 tests PostgreSQL réussis**.
- Les deux échecs décrits dans #129 sont reproduits exactement lorsque
  `ME_LOCAL_REVIEW_ONLY=1` est hérité de l'environnement : 400 au lieu de 200
  pour le test de confidentialité du contact, et `review` au lieu de `prepare`
  pour l'envoi initial. Cela établit une cause suffisante reproductible ; cela
  ne prouve pas la configuration du poste ayant produit le signalement.
- Les classes de tests d'intégration simulée fixent maintenant explicitement
  ce réglage à `0`. Leurs sous-scénarios de relecture locale gardent leur
  activation explicite à `1`. Aucun transport externe réel n'est ajouté.
- Défaut supplémentaire reproduit dans le module JavaScript réel : une réponse
  HTML 200, notamment après expiration, pouvait déclencher un faux message de
  prolongation réussie. Le POST protégé confirme désormais explicitement la
  prolongation du brouillon courant, sans recréer un brouillon expiré.
- Après correction : **389 tests PostgreSQL réussis**, y compris avec le mode
  local hérité à `1` ; **4 tests JavaScript** de prolongation réussis, ainsi que
  les **9 tests JavaScript existants** des filtres/admin et de la recherche métier.
- `make migrate` sur base locale vide puis `make check` : réussis, aucune
  migration supplémentaire. Les tests de migrations aller/retour font partie
  de la suite complète.
- `make users-upgrade-test` a révélé un défaut distinct : le diagnostic
  reconstruisait le schéma historique en incluant le nouveau profil candidat,
  qui dépend déjà des migrations du compte actuel. Il exclut maintenant de
  cette phase les migrations qui dépendent de `users`, puis les applique dans
  la transition normale. Diagnostic rejoué avec succès : quatre relations et
  données d'offre conservées, refus des comptes sans rôle et des collisions
  email, seconde exécution idempotente. `make test TESTS=config.test_test_collection` réussit aussi.
- `make check-js`, `make format-js-check`, `make format-check`,
  `make format-html-check` et `make translations-check` : réussis.

## Validation GitHub préparée

Le workflow PostgreSQL ne couvrait que les PR visant `main`. Le changement
préparé couvre aussi les PR empilées. Il garde les permissions en lecture seule
et la base PostgreSQL fictive du workflow existant. Les tests navigateur simulé
du brouillon sont intégrés à `make check-js`, déjà exécuté par le workflow JS.
Ces changements de workflow ne sont pas encore exécutés sur GitHub.

## Avant fusion / ouverture

- Relire les corrections avec #129, dont la branche source appartient à un fork.
- Terminer la recette manuelle lecteur d'écran, zoom 200/400 % et mobile ; les
  tests DOM simulés ne constituent pas un audit d'accessibilité.
- Valider le contact conseiller ; le lien EURES par défaut reste inchangé.
- Le questionnaire demeure une démonstration en session : raccordement au
  compte/profil, vérification email, notice, conservation et purge restent les
  lots suivants. Aucun matching réel n'est activé.
