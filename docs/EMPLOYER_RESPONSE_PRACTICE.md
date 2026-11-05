# Réponses habituelles aux candidatures — recette locale

## Choix validé le 5 novembre 2026

Deux questions : réponse à toutes les candidatures ou aux seules personnes retenues,
et délai habituel de première réponse, hors accusé automatique. Elles sont liées
au **compte employeur**, jamais partagées automatiquement avec les collègues du
même établissement. Un compte peut avoir sa propre pratique même si un autre
compte appartient au même établissement.

Dans les deux variantes de l'import, à l'étape contact, un employeur sans réponse
enregistrée voit les questions. Le bouton « Enregistrer mes réponses » sauvegarde
cette déclaration indépendamment du dépôt de l'offre. Il faut répondre aux deux
questions pour enregistrer cette fiche ; cela ne bloque pas le dépôt d'une offre.
Après sauvegarde, le récapitulatif remplace les questions. Aux prochaines visites,
il est affiché directement avec « Modifier mes réponses ». Les champs sont alors
préremplis ; « Annuler » restaure les valeurs enregistrées.

## Stockage et droits

Migration additive `employers.0004_employerresponsepractice` : nouvelle table
`employers_employerresponsepractice`, modèle `EmployerResponsePractice`, relation
unique vers `users.User`. Colonnes `response_coverage`, `response_time`, `revision`,
`created`, `updated`. Aucun profil créé pour les comptes existants tant qu'ils n'ont
pas répondu. Valeurs canoniques contrôlées par PostgreSQL ; les libellés FR/EN/DE
restent indépendants du stockage. Consultation et filtres dans l'administration
en lecture seule.

API privée `GET/POST /api/employer/response-practice/` : compte employeur actif
courant uniquement, CSRF conservée. Aucun identifiant de compte soumis ne permet
de choisir la cible. POST JSON : les deux codes et la révision courante, 0 pour
la première déclaration. Retour : codes et nouvelle révision. Une écriture depuis
une ancienne révision est refusée avec 409 ; les erreurs de saisie avec 400,
les comptes non autorisés avec 403. Le contrôle démo existant reste applicable.
Verrouillage du compte dans une transaction pour sérialiser la première création.

## Futures relances : limites explicites

Cette fiche fournit des données exploitables par requête, sans déclencher de
relance ou de recherche. Aucune durée chiffrée n'est inventée pour « plus d'un
mois » ou « délai variable ». Une tranche jusqu'à un mois n'est pas assimilée
silencieusement à 30 jours ni à des jours ouvrés. La politique de calcul des
échéances reste à définir.

Une future candidature devra identifier la personne responsable, sa date de
réception, l'état/date de première réponse et la règle applicable à cet instant.
Modifier cette fiche courante ne doit pas recalculer rétroactivement les échéances.
L'historisation par candidature et l'envoi des relances ne sont pas implémentés.
Les modalités de purge de la fiche restent à raccorder aux règles du compte.

## Vérifications et lancement

- `make employer-response-test` : stockage, reprise, collègues, droits, CSRF,
  codes invalides, conflits de révision et rendus FR/EN/DE des deux variantes.
- `make admin-test` : lecture seule, y compris cette nouvelle fiche.
- `make test` : suite PostgreSQL complète.
- `make check` : Django et cohérence des migrations.
- `make migrate` : application à une base locale dédiée.
- `make test-accounts-seed` : comptes fictifs uniquement avec protections locales.
- `make employer-response-run` : serveur local sur le port 9036, sans email réel.

Dans la recette, choisir un compte employeur fictif, préparer une offre et aller
jusqu'à l'étape contact. Enregistrer les réponses, ouvrir leur modification,
changer un choix puis annuler : les anciennes réponses doivent rester visibles.
Un autre compte du même établissement doit conserver ses propres réponses.
Ce travail n'autorise ni fusion ni déploiement.
