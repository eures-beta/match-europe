# Lot 4A — lancement simulé du recrutement

## Périmètre validé le 22 octobre 2026

Eric accepte le premier sous-lot proposé et précise que le lancement comprend
la recherche de candidats, leur qualification et la prise de contact. La suspension
temporaire des écritures pendant une demande en cours ou incertaine est retenue.
Clôture, archivage, réouverture et leurs droits restent à définir avec lui.
Tout membre actif explicitement habilité à l’établissement peut confirmer le
lancement simulé ou vérifier son état ; aucun droit n’est déduit d’un email.
Ce sous-lot ne crée ni candidatures ni conversations et ne convertit aucun import
en modèle historique `Offer`. Aucun résultat de qualification n’est inventé.

Branche `codex/employer-search-launch`, depuis la tête distante du lot 3
`8ca94ce84ca2738970f3e30acd59f1144b928538`, vérifiée le 22 octobre 2026.
PR #21 toujours ouverte en brouillon, vers `codex/employer-connected-add-offer`.
Code, traductions et instructions locales dans le dépôt public ; aucune donnée
réelle, configuration privée ou procédure d’exploitation.

## Transitions

- Brouillon : modification, consultation, duplication, accès à la confirmation.
- Confirmation GET : aucun lancement. POST avec CSRF, confirmation obligatoire,
  révision courante et scénario de simulation validé côté serveur.
- Demande enregistrée : opération durable avec UUID, révision et auteur ; état
  `pending`. Le scénario simulé répond dans la même transaction.
- Succès confirmé : état `started`, date serveur `search_started_at`, révision
  incrémentée, modification interdite, consultation et duplication conservées.
- Échec certain : état `failed`, sans date de démarrage, révision incrémentée,
  modification possible. Une nouvelle tentative exige une nouvelle confirmation.
- Délai dépassé : état `uncertain`, sans annoncer de démarrage, écritures suspendues.
  Le POST « Vérifier le démarrage simulé » réconcilie l’opération existante, sans
  nouvelle demande. Il confirme le démarrage ou l’échec selon le scénario initial.

La répétition d’un POST de confirmation est rattachée à son opération originale,
même après échec ou modification ultérieure. Une contrainte unique sur
(import, révision) et les verrous PostgreSQL empêchent les doubles lancements.
Le verrou de préparation historique est partagé avec le lancement ; le verrou
sur l’import sérialise modification/lancement. L’appartenance active est également
revérifiée et verrouillée. Les anciennes routes d’écriture refusent aussi les
états pending/uncertain. Les refus n’écrasent pas les données enregistrées.
La copie reçoit un nouvel identifiant ; opérations, événements et dates de
recherche ne sont jamais copiés. Les traces contiennent auteur, objet, état et
dates, sans description d’offre ni coordonnées de contact dupliquées.

## Limites du contrat externe

Contrat public relu le 22 octobre 2026, version v0.42 :
<https://developers.aglae.ai/openapi.json>.
Le calcul de profils suggérés ne lance ni candidature ni qualification.
L’activation d’une offre et le déclenchement de recherche sont distincts ; ce
dernier peut automatiquement engager la qualification. Il ne documente pas de
clé d’idempotence ni de lecture d’une opération de lancement. La désactivation
laisse les qualifications déjà engagées continuer. Une simple relecture d’offre
active ne prouve donc pas le démarrage du moteur de recherche.
Ces limites interdisent de présenter ce sous-lot comme un raccordement réel.
Garanties de répétition, preuve de démarrage et réconciliation à obtenir avant
l’implémentation d’un adaptateur réel. Aucun appel d’activation, recherche,
qualification ou contact n’est présent dans le nouveau module.

## Recette locale et vérifications

Activer les trois modes locaux habituels et `ME_EMPLOYER_SEARCH_SIMULATION=1`.
Le nouveau bouton n’est disponible qu’avec simulation et mode lecture locale
activés ; les routes de lancement/vérification renvoient 404 sinon.
Quatre scénarios : succès, échec avant démarrage, délai dépassé accepté ou refusé.
Tous les écrans concernés portent une indication explicite de simulation.
La suspension des écritures persiste même si le mode simulation est désactivé ;
le réactiver pour vérifier l’opération fictive en attente.

Recette séparée sur 9021 et base PostgreSQL dédiée, comptes fictifs
`rh1@entreprise.invalid` et `rh2@entreprise.invalid`, appartenances créées
explicitement. Aucun changement des recettes 9018, 9019 et 9020.

Validation : 108 tests PostgreSQL réussis, dont huit nouveaux tests de transitions,
répétitions après succès/échec, incertitude acceptée/refusée, anciennes écritures,
droits, CSRF, confirmation, modes locaux, traductions et courses concurrentes
(deux collègues ; modification contre lancement). Migration complète sur base vide.
Contrôle navigateur : connexion fictive, tableau, confirmation, délai dépassé,
vérification du démarrage, verrouillage et duplication en brouillon modifiable.
FR/EN/DE et HTML sémantique conservés ; pas de certification WCAG ou de marque.
Aucun email réel, appel externe de recherche, fusion ou déploiement.
