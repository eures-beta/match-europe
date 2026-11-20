# Décisions actuelles

Choix durables, raisons et références, sans journal d'activité. Toute nouvelle
décision humaine validée précise ce qu'elle remplace et pourquoi.
Les versions précédentes restent dans [Git](https://github.com/eures-beta/match-europe/commits/main/docs/DECISIONS.md).

## D01 — Parité des environnements

Une fonctionnalité métier livrée fonctionne en local, recette et production,
avec les mêmes droits et consentements. L'environnement n'est pas une autorisation.
Cela remplace les anciens contrats de prototype local/loopback/mode démo : leur
réutilisation bloquait des parcours réels après livraison.
Les secrets et transports sont configurables, les simulations explicites ;
un repli guidé prévu est différent d'une simulation silencieuse.
Référence : [contrat de parité](ENVIRONMENT_PARITY.md) ; historique dans Git.

## D02 — Comptes, rôles et données de démonstration

Email unique sans casse ; un rôle `kind` obligatoire, exclusif et immuable :
conseiller, employeur ou candidat. Le compte est le modèle Django fondé sur
`AbstractUser`, sans profil générique supplémentaire ; les profils métier
candidat/employeur restent distincts.
La connexion ne crée jamais de compte. Les conseillers invitent ; le dépôt d’une
offre précrée explicitement un compte employeur actif si nécessaire ;
le candidat confirme son adresse puis la création du compte/profil par POST.
Cela évite les conversions de rôle et les créations implicites.
Les comptes de démonstration sont un outil séparé, jamais une condition d'accès
métier : `DEMO_ACCOUNTS_ENABLED`, local/recette, base fictive, e-mails réels désactivés.
Le même jeu est préparé dans les deux environnements, sans variante `seed_pwa`.
Références : [utilisateurs](USER_MODEL.md), [inscription](CANDIDATE_EMAIL_REGISTRATION.md),
[invitations](INVITATIONS.md), [démonstration](TEST_ACCOUNTS.md), [#191](https://github.com/eures-beta/match-europe/pull/191).

## D03 — Autorisations et administration

Tous les conseillers actifs ont les mêmes droits métier. Les groupes et permissions
Django supplémentaires ne doivent pas bloquer invitation, revue ou suivi.
Propriété des objets, CSRF, consentement et validation restent obligatoires.
L'administration est en consultation même pour les superutilisateurs ; le rôle
métier n'octroie pas d'accès admin. Ces deux décisions limitent les habilitations
incompréhensibles et les modifications accidentelles.
Références : [droits](ADMIN_PERMISSIONS.md), [administration](ADMIN_READONLY.md),
[#188](https://github.com/eures-beta/match-europe/pull/188).

## D04 — Domaines et couche web

Applications métier : users, invitations, candidates, employers, occupations,
skills et matching ; documents, emails, integrations et observability portent
les responsabilités de support selon leur configuration Django.
Vues, formulaires et routes web sont rangés dans `www/` ; les services, modèles,
migrations et validations partagées restent dans leurs domaines et ne dépendent
pas de `www`. Les outils métiers restent dans ces paquets, pas dans `scripts/` racine.
Les tests et helpers sont centralisés dans `tests/`, sans en faire une application.
Cette séparation évite un nouveau monolithe `journeys` et les dépendances croisées
d'interface. Références : [architecture](ARCHITECTURE_WEB.md),
[extractions](DOMAIN_EXTRACTION.md), [tests](TESTS.md), [#202](https://github.com/eures-beta/match-europe/pull/202).

## D05 — Parcours, stockage et décisions humaines

Le questionnaire candidat collecte progressivement projet, compétences, langues,
mobilité, conditions et disponibilité ; il ne réintroduit pas l'import CV abandonné.
Le brouillon temporaire est distinct du `CandidateProfile` durable créé après
vérification ; reprise/comparaison explicite avant remplacement d'un profil.
Les offres sont des `JobOffer` appartenant au compte employeur `created_by`.
Le [compte propriétaire](EMPLOYER_OFFER_OWNERSHIP.md) remplace établissements et
adhésions ; un partage multi-comptes sera conçu séparément.
Le conseiller déposant est conservé dans `adviser` ; l’email existe uniquement
dans le compte, créé actif au dépôt si nécessaire.
Une confirmation téléphonique suffit avant matching. Voir [le dépôt conseiller](ADVISER_OFFER_DEPOSIT.md).
Le matching produit des résultats explicables, avec critères établis/inconnus et
blocages validés ; ne pas déduire automatiquement des pénalités des données absentes
hors règle explicitement revue. La suite de #250 réévalue le métier et les poids
avec priorité aux compétences, selon la grille expérimentale documentée dans
[MATCHING.md](MATCHING.md). La décision conseiller, la réponse candidat et l'accord de
transmission sont distincts. L'avis Albert reste une aide soumise à relecture.
La revue par offre n'est pas la conversation réelle à trois.
Le dialogue demande d'abord l'intérêt pour le poste puis, après ses conditions,
l'intérêt pour l'employeur. Un refus arrête la proposition sans motif obligatoire
ni changement de profil. Les réserves restent dans le résumé à relire avant
l'accord distinct de transmission ; Albert accompagne sans décider.
La finalisation du profil vérifié et ses modifications confirmées déclenchent
le matching après commit contre les offres éligibles déjà enregistrées ; cela
complète le déclenchement côté offre sans modifier les décisions humaines.
Références : [questionnaire](CANDIDATE_JOURNEY.md), [stockage](CANDIDATE_PROFILE_STORAGE.md),
[matching](MATCHING.md), [confirmations](CANDIDATE_OFFER_CONFIRMATIONS.md),
[dialogue](ALBERT_DIALOGUE_ADAPTER.md), [conversation](CONVERSATIONAL_MATCHING.md).

## D06 — Intégrations et e-mails

Albert utilise le transport commun `integrations.albert` ; les prompts et
validations restent dans les domaines. Une clé n'autorise pas des appels réels
dans les tests automatisés. `ALBERT_SIMULATED` est le seul réglage de simulation.
Toutes les fonctions métier sont disponibles par défaut, sans interrupteur par parcours.
Les e-mails passent par le backend Django commun ; `EMAIL_DELIVERY_ENABLED` et
un transport configuré autorisent l'envoi dans tous les environnements.
L'ancienne règle SMTP « production déclarée obligatoire » est remplacée par ce
contrat : ne pas déclarer une recette production pour envoyer un e-mail.
Les liens utilisent une origine de confiance, jamais l'en-tête Host arbitraire.
Références : [Albert](ALBERT_CLIENT.md), [e-mails](MAGIC_LOGIN.md),
[#206](https://github.com/eures-beta/match-europe/pull/206).

## D07 — Référentiels et interface

ESCO/ROME décrivent les métiers ; ESCO porte aussi les compétences.
Conserver sources/version/provenance, références validées et inconnus.
Les choix éditoriaux de savoir-être ne deviennent pas des relations officielles.
Un seul template par page et gettext FR/EN/DE remplacent les générateurs de pages
par langue. Bootstrap est habillé par les tokens ECL du design system EURES ;
les EURES Graphic Guidelines 2022 restent l'autorité de marque.
CSS web externe, exceptions e-mails et catalogue explicitement bornées.
Les routes sont nommées, indépendantes des templates/langues ; les anciens chemins
sont isolés pour compatibilité et ne sont plus émis.
Références : [catalogues](OCCUPATION_CATALOG_MAINTENANCE.md), [compétences](SKILLS.md),
[design system](DESIGN_SYSTEM.md), [CSS](HTML_CSS.md), [API](API_NAMING.md).

## D08 — Données existantes et publication

Une migration publiée reste immuable ; toute évolution est additive, revue et
testée avec des données non vides et, quand applicable, en retour arrière.
Préserver identifiants, relations, droits et données. Les tables actives suivent
`app_label_modelname`, avec fichiers métier, relations, colonnes et objets SQL
cohérents. Les migrations d'harmonisation remplacent l'état de compatibilité des
anciens noms physiques, sans effacer l'histoire ni les contrats cryptographiques.
Les contrôles Django et tests de schéma/aller-retour empêchent cette dette de
revenir ; voir [la convention et les migrations](MODEL_NAMING.md).
Créer une PR n'autorise ni fusion ni déploiement. L'historique reste linéaire,
sans squash sauf demande. La pile active contient seulement les PR destinées
à la production encore ouvertes ; les essais/backups restent indépendants.
Références : [migrations](AUTONOMOUS_MIGRATIONS.md), [validation](TESTS.md),
[procédure des agents](AGENT_WORKFLOW.md).

## D09 — Documentation actuelle, historique Git

Les consignes permanentes sont courtes, les procédures spécialisées chargées à
la demande et le handoff limité à la prochaine reprise. Le détail de chaque
ancienne exécution reste dans Git/les PR/CI, sans copies d'archives Markdown.
Un choix durable conserve ici son pourquoi et son lien de référence.
Les retours sont factuels, actionnables et ne prétendent pas identifier l'IA auteur.
Référence : [politique documentaire](DOCUMENTATION.md), décision de dejafait du
16 novembre 2026 dans la préparation de cette PR.

## 19 novembre 2026 — catalogue métier commun candidat et employeur

Eric valide l’extension du test boulanger : fiches métier sans noms de référentiel ni sources visibles, regroupement fondé sur la table officielle et listes mixtes de compétences. Réalisation locale : regroupements limités aux correspondances exactes non ambiguës de l’intitulé principal ; identifiants de compétences distincts conservés, Albert borné aux relations officielles, liste de référence disponible sans appel IA, validation et cache partagés entre les rôles. Les sélections restent explicites (5 compétences, 3 savoir-être). Les correspondances entre métiers ne valent pas équivalence entre compétences. Voir `COMMON_OCCUPATION_SKILLS.md`. Publication en PR autorisée ensuite ; aucune fusion ni déploiement.

Clôture Albert : synthèse durable, traitement partagé tracé et décisions humaines
avec message candidat distinct des notes internes ; trois refus distincts proposent
une révision du profil, jamais automatique. Voir [le contrat](REVIEW_HANDOFF.md).
