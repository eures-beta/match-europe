# Ligne de vie du matching

Le suivi porte sur un `CandidateOfferMatch` : un candidat et une offre, dès la
création du matching. Il est commun aux conseillers actifs. La revue candidat,
les accords et la conversation à trois sont des étapes de ce même dossier.

## Lire et agir

Le tableau compact présente un matching par ligne ; le nom ouvre sa fiche.
La fiche utilise une frise horizontale et des formulaires repliables.
Le tableau affiche l’étape actuelle, la personne attendue, le temps d’attente,
la date de suivi éventuelle et l’action principale. Les embauches à confirmer
et les échéances arrivées passent en priorité. Les filtres séparent notamment
les dossiers à examiner, les embauches à confirmer et les dossiers terminés.

La fiche présente huit étapes : création, examen conseiller, accord candidat,
validation conseiller, accord employeur, conversation à trois, embauche et
clôture. Chaque état vient des données réelles ; une ancienne étape sans preuve
est indiquée « Non documentée ». Le temps d’attente part de l’entrée dans l’étape,
pas de la dernière relance. Aucun délai de réponse arbitraire n’est imposé.

L’action principale mène directement à l’examen, au dialogue, à la validation,
à l’accord employeur ou à la conversation. Le conseiller peut fixer une date de
suivi sans créer artificiellement une revue candidat. Il peut préparer une
relance sans avoir préalablement enregistré une date.

## Terminer le matching

Dans une conversation à trois ouverte, l’employeur propriétaire peut déclarer
« J’ai embauché cette personne » et une date de début facultative. Cette déclaration
place le matching dans les embauches à confirmer ; elle ne le clôture pas.
Le conseiller vérifie explicitement l’embauche, coche la confirmation puis clôture.
Il peut aussi terminer un matching sans embauche, avec un motif obligatoire.
Une issue terminale ne se réouvre pas par un ancien formulaire.

La conclusion concerne uniquement ce matching : ni profil, ni offre, ni messages
ne sont supprimés ou modifiés. Le fil reste consultable. Les échéances et relances
cessent dès la déclaration d’embauche ; l’action attendue devient sa vérification.
Le tableau de bord conseiller signale les embauches à confirmer.

## Relances et confidentialité

Le conseiller choisit le destinataire, la langue et relit le texte avant envoi
explicite. Avant le fil commun, le lien candidat mène à sa revue privée ou à la
clarification demandée. Une relance employeur exige un accord actuel encore attendu.
Après ouverture, les deux participants peuvent être relancés si les conditions
et accords sont toujours actuels. Refus et absence de réponse restent distincts.
Aucune note privée Albert ou conseiller n’est copiée dans le fil ou l’email.

Le backend Django et `EMAIL_DELIVERY_ENABLED` s’appliquent. L’écran distingue
transport désactivé, tentative, acceptation par le transport et échec ; acceptation
ne prouve ni réception ni lecture. Aucun envoi automatique ni nouvelle tentative
automatique. Verrou, version et intervalle de 60 secondes empêchent les doubles
soumissions ; une réponse reçue invalide un formulaire périmé.

## Stockage et vérification

`MatchFollowup` est lié uniquement au matching ; la revue se retrouve par ce matching.
Le [journal commun `MatchEvent`](MATCH_EVENTS.md) conserve dates, auteurs,
messages et résultats du transport. `MatchConclusion` et les événements de
conclusion distinguent déclaration employeur et confirmation conseiller. Les rôles sont également contrôlés dans PostgreSQL.
L’historique détaillé est réservé aux conseillers, l’admin aux identifiants.

Les migrations additives `0028` à `0033` conservent les plans et événements
existants, avec rattachement par la revue historique. Un retour arrière est
refusé s’il détruirait un plan sans revue ou une conclusion déclarée ; préserver
ces données avant toute opération de retour arrière. Les migrations historiques
`0026` et `0027` restent nécessaires. Les liens utilisent uniquement l’identifiant du matching. Les écrans par revue
remplacés avant livraison sont supprimés, sans alias de compatibilité.

Le rattachement et les protections de retour arrière utilisent exclusivement
la connexion du moteur de migration, y compris sur une base nommée autrement
que `default`. `tests/matching/test_migration_database_alias.py` vérifie ce ciblage ;
`make users-upgrade-test` éprouve la transition complète dans une base isolée.

Recette : `make test TESTS='tests.followup.test_match_lifecycle tests.followup.test_match_lifecycle_migration tests.followup.test_match_followup'`,
puis contrôles communs Python, HTML/CSS et gettext. Le transport réel doit être
vérifié séparément dans un environnement configuré autorisé.
