# Rattachement employeur à un établissement

Le compte employeur se connecte par le [parcours commun](MAGIC_LOGIN.md), importe
son offre, relit les informations et choisit son établissement. Le brouillon est
réservé à son compte dès sa création ; aucun transfert par lien simulé n'est utilisé.

- Un établissement : confirmation explicite de son choix.
- Plusieurs : choix parmi ses appartenances actives, vérifiées côté serveur.
- Aucun : saisie du nom et première appartenance créées sous verrou transactionnel.
- Aucune correspondance automatique par nom, domaine ou adresse email.

Les membres actifs partagent les offres de leur établissement. La révocation retire
les droits à la requête suivante. Le créateur reste tracé ; une ancienne session
anonyme ne permet pas de reprendre le brouillon d'un autre compte.
Les contrôles de révision et CSRF restent nécessaires pour toute modification.

Modèles `Company`, `CompanyMembership` et `JobOffer` : tables, données et relations
conservées. Aucun changement de schéma dans le retrait des parcours historiques.
`make test TEST_ARGS='-k employer -k occupation'` et `make test` vérifient le rattachement et les droits.
