## 13 novembre 2026 — Routes employeur explicites et API job-offers

EMPLOYEURS / TRANSVERSE : accueil, import et notice possèdent des routes nommées
`/employer/`, `/employer/import/`, `/employer/privacy/`. Suppression du serveur
générique de templates ; langue gettext commune et liens canoniques dans les
pages, JS et retours de connexion. API `/api/job-offers/` recâblée sans changer
les données ou les droits. Les anciennes URL sont isolées comme vestiges :
GET/HEAD 301 pour les pages et 308 préservant les POST des anciens clients API.
`/employer/connected/` n'est plus une entrée active ; futur retrait explicite.
Les deux interfaces matching, les invitations et le Push restent inchangés.
Aucun modèle ou migration. Voir [les routes et la compatibilité](docs/API_NAMING.md).

## 13 novembre 2026 — application dédiée aux invitations

TRANSVERSE / CONSEILLERS : le domaine invitations quitte users pour
`eures_beta/invitations/` : modèle, services, formulaires, vues, routes,
administration, commande, templates, styles et tests. Les comptes et la connexion
restent dans users ; la validation commune des origines de liens est dans emails.
`invitations.0001` et `users.0009` déplacent l'état Django sans recréer la table,
copier ou supprimer des lignes. Identifiants, relations, permissions, journal et
liens existants conservés ; transfert réversible. L'historique n'est pas réécrit.
Voir [l'architecture et les migrations](eures_beta/invitations/README.md).

Validation : 600 tests PostgreSQL réussis, dont transfert aller-retour sur
invitations non vides, conservation des anciens liens, ContentTypes, permissions,
attributions et journal ; conflit de métadonnées refusé. Mise à niveau historique
des comptes réussie. Cinq groupes HTTPS Docker verts sous 256 Mio, sans OOM
(pic local arm64 : 172 883 968 octets) ; témoin historique toujours détecté.
Django/migrations, Black, HTML, JavaScript, CSS et gettext vérifiés.

## 13 novembre 2026 — noms des fichiers d’invitation

La documentation commune est `docs/INVITATIONS.md`, avec tous ses liens mis à
jour. Les templates sont rangés par rôle destinataire dans
`invitations/emails/{employer,candidate,adviser}/`. Le premier message s’appelle
`invitation.*`, la relance `reminder.*` ; le conseiller réutilise son template
d’invitation avec le contexte de relance. Chargeur et inclusions actualisés.
Le contenu des messages et leur comportement restent identiques.

## 13 novembre 2026 — noms communs des invitations

PR188 : `Invitation` remplace `EmployerInvitation`, avec `sender`,
`recipient_kind`, `recipient`, relations `sent_invitations`/`invitation` et
`User.organization_name`. Formulaires, templates, services, administration,
permissions et tests utilisent ces noms. Le champ organisation reste un libellé,
pas une signature libre. Aucun changement des droits ni des rôles invités.

Migration réversible native `users.0008_invitation_names` : renomme les données
existantes et leurs métadonnées de permissions, sans recréer les invitations.
Le test sur données non vides vérifie les trois rôles, les relations, dates,
noms, organisation, permissions attribuées, ancien jeton et retour arrière.
L’URL d’acceptation, le sel de signature et la clé de session historique sont
conservés pour les liens déjà envoyés.

Validation : 597 tests PostgreSQL, test de migration renforcé, mise à niveau
historique, Django/migrations, Black, HTML, JS et gettext verts. Cinq parcours
HTTPS Docker réussis sous 256 Mio (pic 179027968 octets), aucun OOM/SIGKILL.
Services externes simulés ; aucune fusion ni modification de base distante.

## 13 novembre 2026 — tests centralisés à la racine

TRANSVERSE : tous les tests automatisés Python et JavaScript sont sous
`tests/`, classés par domaine. Les contrôles communs sont dans `tests/common/`,
ceux du socle dans `tests/config/`, le banc HTTP Docker dans `tests/e2e/`.
Ce sont des paquets de tests, sans application Django supplémentaire.
Imports, fixtures, sélection Make, CI et guides suivent les nouveaux chemins.
Le peuplement fictif utilisable par les recettes reste du code applicatif.
Aucun changement métier, modèle, migration ou donnée persistante.
Voir [le guide des tests](docs/TESTS.md).

Validation : inventaire identique de 635 tests Python distincts avant/après
déplacement ; suite PostgreSQL et 21 tests Node réussis. Le banc HTTP Docker
passe ses cinq groupes sous 256 Mio sans OOM (pic local arm64 : 181 874 688 octets),
et le témoin historique détecte toujours l'OOM attendu. Mise à niveau historique
des comptes réussie ; Black, djLint, Prettier JS/CSS, syntaxe JS et gettext verts.

## 13 novembre 2026 — conversations partagées compatibles avec les modèles actuels

CONSEILLERS / CANDIDATS / EMPLOYEURS : les fils partagés utilisent
`CandidateOfferReview` ; les contrôles de rôle et des trois participants sont
conservés, sans permission métier Django supplémentaire. L’avis conseiller
utilise le transport Albert commun, avec les limites du dialogue.

La migration `matching.0008_sharedconversation_sharedmessage` suit
`0007_candidate_offer_review_answer_dialogue`. Elle crée les tables sur base
neuve ou adopte celles d’une ancienne recette uniquement avec l’enregistrement
exact `0007_sharedconversation_sharedmessage` et un schéma PostgreSQL équivalent
(colonnes, clés, contraintes, index). L’adoption conserve lignes, identifiants,
relations, dates et compteurs de lecture ; son retour arrière garde ces tables.
Une création neuve est réversible par suppression des nouvelles tables.
Des tests couvrent les données non vides, les séquences, les retours arrière
et le refus de tables partielles ou incompatibles. Aucune base distante modifiée.

## 13 novembre 2026 — migration du dialogue après renommage des modèles

CANDIDATS / TRANSVERSE : le champ JSON `CandidateOfferReviewAnswer.dialogue`
est ajouté par `matching.0007_candidate_offer_review_answer_dialogue`, après
le renommage déjà livré dans `0006_candidate_offer_model_names`. Une ancienne
recette ayant appliqué `0006_confirmationanswer_dialogue` garde sa colonne et
son contenu : adoption uniquement avec cet enregistrement exact et un schéma
JSONB non nullable sans défaut persistant. Une colonne inattendue, manquante ou
incompatible bloque la migration sans écrasement. Le retour arrière d’une
adoption conserve la colonne historique ; celui d’une création neuve la retire.
Tests PostgreSQL dédiés : création neuve, adoption non vide, retours arrière
et refus des schémas inattendus. Aucun changement de base distante.

## 13 novembre 2026 — transport Albert commun à tous les usages

TRANSVERSE : import d’offre, dialogue candidat et compétences ESCO passent par
`integrations.albert.complete_json`. URL, authentification, redirections, budgets
et décodage sont centralisés ; prompts et validations restent dans les domaines.
Le modèle dédié et les limites plus strictes du dialogue sont conservés, ainsi
que la simulation et le cache des compétences. Aucun secret, réglage distant,
modèle ou migration changé. Voir [le contrat](docs/ALBERT_CLIENT.md).

## 13 novembre 2026 — commandes de tests paramétrables

TRANSVERSE : les sélections Django passent par `make test TESTS=...` ou
`TEST_ARGS='-k motif'`, les tests Node par `make test-js JS_TESTS=...`.
Sans paramètre, chaque commande lance toute sa suite. Les 44 alias de sélection
sont retirés ; documentation et CI emploient les mêmes entrées. Les dispositifs
Docker E2E et le diagnostic de mise à niveau historique restent distincts.
Huit tests de contrat vérifient la sélection, les options, les échecs et le
refus d'une sélection vide. Aucun changement métier, modèle ou migration.
Voir [le guide des tests](docs/TESTS.md).

## 13 novembre 2026 — retrait des trois modèles employeurs hérités

EMPLOYEURS / ADMIN : après retrait des parcours obsolètes, suppression de
EmployerEmailLink, EmployerSearchOperation et EmployerSearchEvent et de leur
administration. La migration employers.0007 exige trois tables vides et refuse
sinon toute suppression ; les migrations historiques restent en place.
Company, CompanyMembership, EmployerProfile et JobOffer sont conservés.
Le verrouillage par search_started_at reste actif, sans les états du simulateur.
Aucune fusion ni intervention sur une base distante par ce changement.
Voir [le contrat de retrait](docs/EMPLOYER_SEARCH_LAUNCH.md).

## 10 novembre 2026 — retrait des parcours de démonstration hérités

Sur demande de dejafait, retrait de la connexion employeur indépendante et de sa
boîte simulée, du diagnostic Push (HTML/JS/API/service worker), du simulateur de
lancement de recherche et de leurs routes. Les helpers encore utilisés sont
déplacés dans employer_workspace ; l'espace emploie la connexion/déconnexion
commune. Les droits, CSRF, révisions, rattachements et propriétés restent contrôlés.
Les cinq variables ME_DEMO_MODE, ME_SHARED_DEMO, ME_EMPLOYER_DEV_ACCESS,
ME_EMPLOYER_EMAIL_LOCAL et ME_LOCAL_REVIEW_ONLY ne sont plus consommées.

Les modèles/tables/données historiques restent présents, sans nouvelle écriture
depuis les parcours retirés ; les verrous d'offres déjà en attente sont conservés.
Aucune migration ni purge. Les comptes fictifs et fournisseurs simulés explicitement
activés restent des outils de test isolés ; les modes de présentation sont retirés.
Les actions AGLAE sandbox/géocodage restent explicites et configurées ; la lecture
et la sauvegarde seules ne les appellent pas. Aucun service réel activé ou appelé.

Tests adaptés aux comptes réels de fixtures ; make test TESTS=tests.config.test_retired_paths remplace
l'ancien contrôle de modes. Dépendances Web Push retirées ; cryptography est déclarée
explicitement pour le fixture TLS E2E qui la recevait indirectement. Guides actifs
réécrits et traductions inutilisées retirées, notamment les avertissements hérités.
L'erreur email traduite reste portée par le formulaire commun après retrait de
l'ancien écran qui fournissait sa traduction.

Validation finale après réancrage sur184 sans182 :581 tests PostgreSQL verts ;
huit tests de la nouvelle cible également vérifiés avant réancrage,
Django/migrations, Black, HTML, JS/CSS et gettext verts. Banc Docker Linux arm64 :
cinq groupes de parcours HTTP réels, huit recherches froides, pic166162432octets,
aucun OOM/SIGKILL ni redémarrage worker. Premier essai sans dépendance TLS explicite
échoué au fixture, corrigé puis banc vert. Pas de revue visuelle navigateur.
Aucune fusion ni opération de production autorisée/exécutée dans ce lot.

## 10 novembre 2026 — réancrage du banc après fermeture de #182

Le banc est réancré sur #181, sans reprendre le transport Brevo de #182 fermée.
Les trois commits initiaux sont conservés. Un défaut du lecteur d’e-mails de test
est corrigé : plusieurs messages peuvent partager le même fichier Django.
`make test TESTS=tests.e2e.test_journeys` reproduit ce cas ; échec observé avant correction, puis succès.
Validation après réancrage : 615 tests PostgreSQL et contrôles de qualité réussis.
Les cinq parcours Docker passent sous 256 Mio ; le témoin historique constate
l’OOM attendu à huit recherches simultanées. Aucune fusion ou production effectuée.


## 10 novembre 2026 — parcours HTTP sous plafond mémoire

TRANSVERSE : `make e2e-test` lance les parcours employeur, conseiller et candidat
sur Gunicorn/PostgreSQL isolés, avec un plafond cgroup de 256 Mio pour le serveur.
Huit recherches ordinaires simultanées à froid utilisent les JSON complets ;
PDF, client Albert HTTPS, emails capturés, confirmations et sauvegardes sont
vérifiés. Albert et le transport email sont des frontières externes simulées.
`make e2e-regression` exécute le code historique avant #177 : OOM/SIGKILL détecté,
alors que le code corrigé passe. Une recherche seule ne reproduit pas le kill
localement ; le témoin porte explicitement sur huit recherches concurrentes,
une par thread (quatre ne suffisent pas sur le premier essai CI amd64).
Ce sont des parcours HTTP, sans exécution JavaScript de navigateur. Le job ajouté
au workflow avant déploiement vérifie les deux cas. Aucun modèle, migration,
secret ou comportement applicatif modifié. Voir [le guide](docs/E2E_TESTS.md).

## 10 novembre 2026 — formatage des CSS autonomes

TRANSVERSE : le même Prettier que le JavaScript couvre les feuilles `.css` du
projet via `make format-css` et `make format-css-check`, exécuté aussi en CI.
Les ressources tierces sous `eures_beta/static/vendor/` restent exclues et intactes.
Les feuilles existantes sont reformatées ; aucun changement de style voulu,
modèle, donnée ou dépendance ajouté. djLint conserve les styles dans les templates.
Validation locale : format et stabilité des 16 CSS, format et syntaxe JavaScript,
14 tests JS de `make check-js` réussis. Suite Django non rejouée pour ce lot
limité au formatage et à l'outillage. Aucune fusion ni opération de production.
Voir [le guide](docs/JAVASCRIPT_FORMATTING.md).

## 10 novembre 2026 — calcul à l’enregistrement d’une offre (#180)

Une offre complète rattachée à un établissement déclenche le calcul après
enregistrement pour les profils actifs et vérifiés. Le tableau du matching
existant permet de filtrer par offre et de trier les résultats par score.
Les brouillons privés et les copies non modifiées restent hors calcul. Les
décisions sont conservées et les confirmations candidat exigent toujours
une offre validée. Le calcul s’effectue après validation de la transaction,
dans la requête employeur. Son coût augmente avec le nombre de profils éligibles.

## 10 novembre 2026 — reprise du schéma historique des confirmations

Correctif de #162 : un premier commit reproduit en PostgreSQL la collision
« matching_confirmationrequest already exists » ; le suivant adapte la migration
0005 pour reprendre les trois tables de l’ancienne 0003 uniquement après contrôle
du schéma et de son enregistrement. Aucun effacement ni fake. Neuf tests vérifient
les données non vides, les identifiants et tables conservés, l’aller-retour, les
séquences, l’installation vierge et le refus des divergences. Voir
[le contrat de migration](docs/CANDIDATE_OFFER_CONFIRMATIONS.md).

## 10 novembre 2026 — dialogue Albert sur les confirmations de la #162

La #163 se rattache aux demandes du matching existant. Le candidat doit être
propriétaire de la demande, avec un profil vérifié et une offre validée.
Le formulaire guidé reste accessible et les propositions Albert sont soumises
à validation explicite. Voir [le raccordement](docs/ALBERT_DIALOGUE_ADAPTER.md).

## 10 novembre 2026 — confirmations candidat sur le matching de main

La #162 reprend les permissions existantes du matching et ajoute la confirmation
par offre et l’accord de transmission séparé. Le portefeuille et le modèle
d’équipe de la #161 sont reportés. Voir [le parcours et la migration](docs/CANDIDATE_OFFER_CONFIRMATIONS.md).

## 9 novembre 2026 — questionnaire ouvert, email à la fin

PR fille de #132, en remplacement de #164 fermée sans fusion. Entrée anonyme,
lien pour retrouver un profil, brouillon conservé pendant la vérification et
récupérable sur un autre appareil. Profil existant : comparaison puis choix
explicite, avec contrôle de version pour empêcher un écrasement concurrent.
Autre rôle : aucune conversion, brouillon récupérable pour changer d’adresse.
Migration des demandes vers les sessions Django avant suppression de leur modèle.
Aucun compte/profil existant supprimé. Aucun réglage de production modifié.
Voir [le fonctionnement et les limites](docs/CANDIDATE_EMAIL_REGISTRATION.md).
## 9 novembre 2026 — livraison dans tous les environnements

Décision d’Eric : retirer les restrictions arbitraires local/recette/production des fonctionnalités métier. Configuration et droits réels conservés, fonctionnalités actives par défaut, simulations explicites. Autorisation explicite reçue pour les trois usages Albert, les accès propriétaires employeur et le transport commun des e-mails configuré dans chaque environnement. La pile distante a été actualisée sans perdre les correctifs publiés en parallèle. Validation locale : 605 tests PostgreSQL réussis après intégration du client Albert partagé ; aucun appel Albert ou e-mail réel, aucune fusion ni opération de production. Voir [le contrat actuel et les prérequis](docs/ENVIRONMENT_PARITY.md).

## 9 novembre 2026 — correction de la parité des environnements

La décision d’Eric remplace les anciennes limites de prototype ci-dessous : les fonctionnalités métier sont destinées au local, aux recettes et à la production, avec les mêmes droits. L’import Albert est actif par défaut, sans dépendance au mode démo ni aux e-mails. Une clé privée reste nécessaire aux appels réels ; le repli manuel est conservé. Les outils fictifs restent isolés. Aucune fusion ni opération de production n’est réalisée par cette correction.

## 9 novembre 2026 — séparation du client Albert (#146)

À la demande de dejafait, le client HTTP partagé est dans `integrations/albert.py`.
Le prompt et la validation employeur restent dans `employers/offer_structuring.py`.
Même protocole, mêmes délais/limites et mêmes protections ; aucun appel réel requis.
## 9 novembre 2026 — transport e-mail partagé

Déplacement sans changement fonctionnel de `users/email_backend.py` vers
`emails/backend.py`, avec réglages, imports et tests recâblés. SMTP Django
indépendant de Brevo ; activation explicite identique dans tous les environnements.
Aucun secret, modèle ou migration modifié. Tests : `make test TESTS=tests.emails`.

## 9 novembre 2026 — profil du compte employeur (#133)

À la demande de dejafait, `EmployerResponsePractice` devient `EmployerProfile`,
avec le champ `user` et l'accès inverse `user.employer_profile`, en parallèle de
`CandidateProfile`. Il décrit le compte personnel, pas l'entreprise. Relation
zéro ou un profil par compte, créée lors des premières réponses ; aucune création
automatique. Migration de renommage réversible, sans perte des réponses existantes.
Les questions, l'API, les droits et les règles de validation restent inchangés.

## 8 novembre 2026 — scores et résultats du matching visibles

TRANSVERSE : Eric demande une présentation comparable à Flask. Lecture de
l’administration Flask puis adaptation locale : ligne candidat/employeur/poste,
score global /100 visible, sous-scores, statuts et trois rubriques d’explication.
Aucune modification des poids, blocages, décisions ou droits. Trente tests matching
PostgreSQL réussis, contrôle navigateur et petit écran 390 px. Aucun envoi,
publication ou déploiement distant. Voir [le contrat de matching](docs/MATCHING.md).

## Vérification du matching local — 7 novembre 2026

Base #159 `c39c728`. Matching accessible localement sur le port de recette 9041.
537 tests PostgreSQL réussis, dont 28 ciblés matching ; ces 28 ont été réexécutés
avec succès après le dernier ajustement de template. Vérifications Django et
migrations : aucune anomalie ; Black, djLint, contrôle de structure HTML et
catalogues FR/DE vérifiés. Navigateur : consultation, valeurs comparées, refus
fictif conservé après recalcul et blocage de date avec action de rétention désactivée.
Scénario A conserve un refus fictif issu de cette vérification. Pas d’audit complet
WCAG ni de calibration métier des poids. Guide : [matching](docs/MATCHING.md).
Préparation de l’étape suivante : [dialogue candidat](docs/CONVERSATIONAL_MATCHING.md),
contrat écrit uniquement, pas d’appel Albert ni de notification.

## 7 novembre 2026 — matching local autorisé

TRANSVERSE / CANDIDATS / EMPLOYEURS : Eric autorise le matching local avant
l’outil conversationnel. Base de pile #159 (`c39c728`) vérifiée ; aucune publication,
fusion ou recette distante autorisée. Correspondances, inconnus, trois blocages
explicites et décisions humaines distinctes. Métier hors score ; poids expérimentaux,
pas de classement ni seuil de rejet validé. Albert et ses confirmations par offre
ou générales restent à développer. Voir [contrat et recette](docs/MATCHING.md).

## 7 novembre 2026 — publication et recette regroupée autorisées

Eric demande une nouvelle PR au-dessus de #157, une recette jetable de sept jours de cette PR et la fermeture de la recette de #157. Raccordement étendu à preview HTTPS explicite, données fictives, Albert simulé et e-mails réels désactivés. Aucune fusion ou production autorisée.

## 7 novembre 2026 — parcours continus de recette

Branche locale `codex/continuous-skills-journeys` sur #157 `da5b1c4` revérifié sur GitHub. Composant commun dans les formulaires habituels, stockage dans le JSON offre et champ candidat dédié (migration additive 0005), récapitulatifs et modification. Recette sur 9040 depuis l’accueil ; ancien pilote9039 conservé séparément. Simulation forcée des appels Albert, confirmation candidat locale par POST privée à la session et limitée aux adresses .invalid. Voir [contrat](docs/CONTINUOUS_JOURNEYS.md). Validation finale et limites consignées dans ce document après les contrôles.

## 6 novembre 2026 — compétences des métiers hors sélection

Branche locale `codex/albert-occupation-skills`, sur #156 `f007a7f` vérifié sur GitHub. Pilote employeur/candidat étendu avec recherche ESCO, confirmation, attente, validation stricte des URI parmi les relations officielles et cache PostgreSQL partagé versionné. Migration additive, administration en lecture seule, réservations contre les doubles appels, repli préservant le brouillon. Simulation par défaut ; aucun appel Albert réel ni modification d’offre/profil métier. Voir [périmètre et recette](docs/ALBERT_SKILLS.md). Validation : 491 tests PostgreSQL réussis, 12 tests dédiés et 8 tests admin revérifiés, test JavaScript d’attente réussi ; contrôles Django/migrations/formats/traductions et archives officielles vérifiés. Recette navigateur employeur/candidat, conservation FR/EN/DE et largeur 390 px sans débordement. Aucun audit WCAG exhaustif, appel Albert réel, publication ou production.

## 6 novembre 2026 — commandes de mise à jour des référentiels

## 6 novembre 2026 — implémentation du projet candidat ouvert

Travail autorisé dans une nouvelle PR au-dessus du sommet #155 (`692eb517`). Mode sans métier, sélection 10/5/exactement 3 avec minimum technique combiné de 1, recherche et étiquettes FR/EN/DE. Déclarations canoniques en session, demande temporaire et profil privé ; migration additive 0004 avec conservation des anciens profils. Recette navigateur locale FR/EN/DE, clavier et 390 px effectuée, sans audit WCAG complet. 479 tests PostgreSQL réussis, dont 9 scénarios dédiés au projet ouvert et un nouveau scénario de migration ; 3 tests JavaScript dédiés réussis. Installation sur base vide, contrôles Django/migrations, format Python/templates/JavaScript et catalogues FR/DE vérifiés et compilés. Recette navigateur trilingue et mobile effectuée ; aucun audit WCAG complet. État CI distant à vérifier après publication. Aucun matching, fusion, déploiement ni email réel. Voir [contrat](docs/CANDIDATE_OPEN_SKILLS.md).

## 6 novembre 2026 — validation utilisateur du pilote compétences

Eric a testé et validé le parcours local à un métier, puis autorisé sa publication
en PR sous le titre « Ajout des compétences par métier ». Le multi-métiers
candidat reste une évolution distincte non implémentée. La base de livraison
#151 a été revérifiée inchangée avant publication. Aucune fusion ni aucun
déploiement ne sont autorisés par cette publication.

## 6 novembre 2026 — sélection de compétences à tester localement

Branche `codex/skills-selection-pilot`, créée sur le sommet GitHub vérifié de la
pile ouverte : PR #151, `codex/dedicated-public-views`, commit `4021fbe`.
Deux rôles de simulation, six métiers et variante nettoyage de locaux, huit
compétences et quatre savoir-être proposés ; plafonds serveur/navigateur 5/3,
relecture, modification, conservation FR/EN/DE et séparation des brouillons.
Recette `make skills-pilot-run` sur le port 9038. Aucun e-mail ni service externe,
aucune création d’offre, compte ou profil ; pas de nouvelle migration.

Validation locale : 469 tests PostgreSQL réussis ; reconstruction des deux JSON
identique depuis les archives officielles épinglées FR/EN/DE. Vérification
navigateur réalisée sur les parcours employeur et candidat, plafonds, relecture,
conservation FR/EN/DE et action clavier ; contrôle à 375 pixels sans débordement
horizontal constaté. Ce contrôle n’est pas un audit WCAG exhaustif. La sélection
éditoriale et les libellés sont à revoir avec Eric. Voir
[les limites et commandes](docs/SKILLS.md). Aucun push, fusion ou déploiement.

## 6 novembre 2026 — accroches accueil, candidat et employeur

Branche `codex/editorial-headlines`, au-dessus de `codex/remove-aglae-mentions`
(PR #134, sommet de livraison vérifié sur GitHub au démarrage, `2561176`).
Les trois écrans ont été validés séparément par Eric avant modification du code.
Textes FR/EN/DE harmonisés, parcours candidat/employeur remontés sous l’accroche
d’accueil, signature commune et indisponibilité du matching explicites.
Promesses d’accompagnement systématique retirées des landing pages ; double accord
et absence de rejet automatique sur les seules réponses conservés.
Liens, protections, logos et parcours existants préservés ; aucune migration.

Validation locale du sous-ensemble des pages d'entrée : 17 tests PostgreSQL réussis,
`make check`, `make translations-check`, `make translations-compile`,
`make format` et `make format-html-check` réussis.
Pas d’audit WCAG complet ni de vérification de production. Aucune fusion ou
action de déploiement. Voir les formulations dans `docs/DECISIONS.md`.

PR depuis main : commandes Django `sync_esco`, `sync_rome`, `sync_esco_rome`,
exposées par les cibles `make occupations-sync-esco`, `make occupations-sync-rome`
et `make occupations-sync-esco-rome`. Imports explicites des exports officiels
en staging local, rapport d’écarts et empreintes, sans écriture en base ni Git.
ROME/OGR restent synchronisés sur la même source ; relations ESCO/ROME recalculées.
Les trois téléchargements réels ont reproduit les données embarquées sans changement.
Les compétences restent hors périmètre. Voir la procédure de maintenance.
Validation après rebase sur main : 383 tests PostgreSQL, transition utilisateurs,
contrôles Django/migrations, Black, HTML, JavaScript et traductions réussis.
La cible de promotion a été exercée vers un répertoire jetable, sans modifier
les données versionnées ; 31 recherches multilingues et les empreintes vérifiées.

## 6 novembre 2026 — référentiels JSON lisibles

Les deux gzip du catalogue sont remplacés par quatre JSON UTF-8 indentés :
métiers ESCO, fiches ROME, appellations OGR et correspondances ESCO/ROME.
Égalité intégrale des objets avec les anciens fichiers décompressés vérifiée
avant suppression. Sources, éditions et identifiants conservés ; manifeste v2.
Le chargeur conserve son interface et contrôle les quatre empreintes. L’outil de
reconstruction produit le même format. Aucun modèle ni migration modifié.

## 6 novembre 2026 — prototype local Albert employeur

Branche locale au-dessus du sommet GitHub vérifié de la pile de livraison. Lecture PDF/OCR locale puis structuration Albert ou texte collé, extraits vérifiés, repli manuel et notice FR/EN/DE. Recherches ESCO/ROME séparées ; métier central pour la requête initiale et classement contextuel ROME. Aucun modèle ni migration. Essai réel PDF effectué et contrôles automatisés sans réseau ajoutés. Voir [périmètre, validations et limites](docs/ALBERT_IMPORT.md). Eric doit tester localement avant tout push/PR. Aucune publication ni recette distante effectuée.

## 5 novembre 2026 — réponses aux candidatures par compte employeur

Branche locale `codex/employer-response-time` créée depuis le sommet GitHub
vérifié #132 (`7475889`), les PR de livraison #127 à #132 étant ouvertes et
l'essai #126 exclu. Deux questions à l'étape contact dans les deux variantes
d'import, FR/EN/DE. Nouvelle table `EmployerResponsePractice`, une fiche par
compte employeur ; deux collègues du même établissement restent indépendants.
Après enregistrement : récapitulatif, CTA « Modifier mes réponses », champs
préremplis et annulation. API privée avec CSRF, révision et transaction ;
administration en lecture seule. Pas de changement des données des offres.
Voir [le contrat et les limites](docs/EMPLOYER_RESPONSE_PRACTICE.md).

Validation locale du lot : 419 tests PostgreSQL réussis, dont huit tests ciblés
sur ces réponses et les scénarios de lecture seule administrative étendus.
Migration additive appliquée sur base locale vide, contrôles Django/migrations,
Black, djLint, structure HTML, syntaxe/format JavaScript et traductions réussis.
Recette navigateur sur 9036 : première déclaration enregistrée, récapitulatif,
modification préremplie, annulation sans perte et reprise après rechargement
vérifiés. Compte et offre fictifs uniquement. Contrôle visuel à la largeur
courante du navigateur ; pas d'audit exhaustif lecteur d'écran/WCAG.
Les tests de migration de renommage restaurent maintenant toutes les feuilles
pour ne pas laisser la nouvelle table absente dans les tests suivants.

Les futures relances ne sont pas implémentées : réception, responsable, première
réponse et règle de délai par candidature restent à raccorder. Aucun seuil
numérique inventé pour « plus d'un mois » ou « variable ». Aucun push, fusion,
déploiement ni email réel. Serveur local : `make employer-response-run`.

## 4 novembre 2026 — fluidité et accessibilité : inscription entreprises et parcours candidat

PR empilée sur #128, titre fourni par l’utilisateur. Revue navigateur, données fictives.
Candidats : titre de page par étape (« Erreur — » si besoin) ; récapitulatif d’erreurs
avec liens, focus et ordre de la page ; mentions « obligatoire » des questions
conditionnelles ; `autocomplete` nom/e-mail ; brouillon de 30 min glissant (dernière
action) avec avertissement 2 min avant et bouton de prolongation ; « Modifier : <rubrique> »
qui ramène au récapitulatif. Entreprises : invitation annoncée dès l’accueil et sur
l’accès et la connexion, avec lien « Trouver un conseiller EURES » (`ME_EMPLOYER_ADVISER_CONTACT_URL`,
portail EURES par défaut) ; message unique « compte créé » et première étape guidée sur
le tableau de bord ; e-mail du contact pré-rempli avec celui du compte connecté.
Aucune migration, aucune règle de création de compte modifiée. Pas d’audit RGAA complet :
lecteur d’écran et zoom restent à tester. 2 échecs préexistants dans l’import employeur
(`test_employer_contact`, `test_employer_import`), présents avant cette PR.

## 4 novembre 2026 — premier lot des comptes candidats

Branche `codex/candidate-account-kind` depuis `origin/main` (`070038d`), vérifié
sur GitHub : aucune PR de livraison ouverte, seule #126 de recette jetable.
Ajout de `User.Kind.CANDIDATE` et migration `users.0005_candidate_kind` pour
étendre la contrainte PostgreSQL. Rôle immuable et email unique conservés,
aucun privilège supplémentaire. Le tableau de bord candidat utilise la page
générique existante sans entrer dans l’espace employeur. FR/EN/DE couverts.

Validation du lot : `make test TEST_ARGS='-k test_users -k candidate_kind -k closed_registration'` (21 tests PostgreSQL réussis), puis
`make test` (364 tests PostgreSQL réussis), `make check`, `make format-check`,
`make translations-check` et `git diff --check`. Migration depuis `users.0004`
testée avec conservation intégrale des comptes conseiller/employeur, rejet
des rôles invalides, unicité email et immuabilité SQL. Retour à `0004` testé
après retrait du seul candidat fictif ; aucun effacement automatique prévu.
La première suite complète a échoué sur l’observabilité après désactivation
locale de l’échantillonnage ; réglages locaux rétablis, suite complète réussie.
Worktree et base de test locaux dédiés ; aucune donnée réelle modifiée.

Choix d’Eric confirmé pendant le travail : champs et tables dédiés pour les
réponses utiles au matching. Prochain lot : profil courant lié au compte,
réponses structurées et validations partagées avec le questionnaire. Puis
dépôt anonyme, création du compte en fin de parcours et vérification email.
Ce premier lot ne crée ni profil persistant ni compte depuis une page publique.
Aucun push, PR nouvelle, fusion, déploiement ou email réel.

## 3 novembre 2026 — consultation de tous les modèles dans Django Admin

PR dédiée depuis main : neuf modèles applicatifs et cinq modèles techniques
consultables par les superadministrateurs. Administration entièrement en lecture
seule, y compris les comptes ; création de conseiller par admin retirée.
Invitations employeurs hors admin inchangées. Secrets exclus, sessions et journal
limités à leurs métadonnées. Aucune migration ou donnée de production modifiée.
Voir docs/ADMIN_READONLY.md et `make test TESTS=tests.users.test_readonly_admin`.

## 2 novembre 2026 — invitations employeurs (nouvelle PR)

Conseillers : liste paginée des employeurs et invitations, création d'invitations
de sept jours. Compte employeur créé seulement après confirmation POST/CSRF,
sans mot de passe ni droits administratifs. Groupe de droits versionné ; table
additive EmployerInvitation. Tableau employeur conservé en construction.
Connexion habituelle prolongée à une heure ; session glissante de trente jours
inchangée. Aucun prestataire mail activé. Commandes privées de simulation via
Makefile, jamais de lien secret dans les pages. Voir docs/INVITATIONS.md.

## 2 novembre 2026 — diagnostic des performances

PR transverse au-dessus de #103 : middleware de bilans JSON, agrégats SQL et
étapes d’import bornées, X-Request-ID et hook Gunicorn avant arrêt du worker.
Pas de contenu métier ni données de connexion dans les nouveaux événements.
Seuil et échantillonnage configurables, sondes et statiques exclus. Aucune
modification des délais, instances ou données de production. Voir
[les mesures et leurs limites](docs/OBSERVABILITY.md).

## Fermeture de la création autonome de comptes — au-dessus de #100

La validation d’un lien ne crée plus d’utilisateur. Les demandes ne produisent
un lien que pour un employeur existant et actif ; inconnus, conseillers et
comptes désactivés reçoivent la même confirmation générique sans jeton.
Formulaires et anciens liens couverts par des tests serveur ; ni invitation,
ni liste blanche implémentée ici. Administration habilitée et opérations
internes conservées. Voir docs/ACCOUNT_REGISTRATION.md. Pas de migration ni
de changement de données de production.
Validation : 211 tests PostgreSQL, huit tests ciblés de fermeture, contrôles
Django/migrations, Black, HTML, JavaScript et gettext réussis.

## 2 novembre 2026 — rafraîchissement de la PR utilisateurs sur la consolidation

Rebase sur le main contenant la référence autonome c9034fd. Conservation du
chargeur de tests historiques, isolation des vérifications de la consolidation
avant le transfert des identités, et scénario de mise à niveau avec marqueur
autonome. 217 tests PostgreSQL, 16 tests ciblés de migration, mise à niveau
jetable et contrôles de qualité réussis. Aucun changement en production.

## 2 novembre 2026 — préparation du compte utilisateur unique

PR de remplacement d’EmployerIdentity par users.User(AbstractUser), avec `kind`
conseiller/employeur obligatoire et immuable, e-mail unique sans casse et sessions
Django. Les relations employeur sont transférées ; les comptes auth.User sans
rôle connu bloquent la transition. Aucun changement d’accès public ni Brevo.
Voir [la transition, les vérifications et la limite de retour arrière](docs/USER_MODEL.md).
Travail sur branche dédiée, sans fusion ni écriture en production.
Validation locale : 213 tests PostgreSQL, contrôles Django/migrations, Black,
djLint, JavaScript et gettext réussis. Mise à niveau réelle dans une base locale
jetable : garde-fous, conservation des données et relance des migrations vérifiés.

## 2 novembre 2026 — contenu de la page Projet

Branche locale `codex/project-page` empilée sur `codex/directory-readmes` (#92,
`e16ff0b`), seule PR ouverte vérifiée au démarrage. Reprise des textes FR/EN/DE
servis par la page historique FT `forms/eures-beta/le-projet` et son `app.js`.
Template Django/gettext dans le cadre public existant, sommaire à quinze entrées,
sections, listes, exemple fictif, réserves sur les chiffres et canaux envisagés.
La reprise éditoriale ne valide pas à nouveau les résultats historiques ni les
chiffres de cadrage. Aucune donnée personnelle, migration ou appel externe à
l’affichage. Statistiques et journal restent en construction. Validation locale : 223 tests PostgreSQL réussis, contrôles Django et absence
de migrations, Black, djLint, structure HTML, catalogues gettext et collecte
statique réussis. Comparaison exhaustive des textes des quinze sections en
FR/EN/DE avec les réponses locales : aucune omission. Sommaire et bascule de
langue vérifiés au navigateur local ; pas d’audit WCAG/marque complet.
Aucun push, fusion ou déploiement.

## 30 octobre 2026 — information commune du parcours employeur

Sur la base de la PR #79 (`ef51200`), branche `codex/employer-wip-feedback` :
bandeau unique FR/EN/DE pour accueil, imports classique/V2, confidentialité et
enveloppe de connexion/espace employeur (offres, détail, édition, duplication).
Adresse de retour visible/cliquable, logo Match Europe existant sur l’accueil et
étapes distinguant enregistrement et rapprochement prochainement disponible.
Le JavaScript d’import ne remplace plus le bandeau ; l’injection de l’ancien
avertissement générique est réservée au diagnostic Push privé.

Les indications factuelles sur les emails simulés et la notice de confidentialité
non validée restent conservées. Aucun changement des données, habilitations,
authentification ou intégrations. L’enregistrement est présenté conformément à
la demande d’Eric ; la conservation distante n’est pas vérifiée par cette PR.
Une recette jetable ne garantit pas une conservation durable des offres.

Validation : 21 tests ciblés réussis sur PostgreSQL local (pages FR/EN/DE,
connexion, démo partagée et protections hors démo), contrôle gettext, compilation,
formatage et diff. 33 rendus de templates contrôlés et rendu bureau FR vérifié.
Eric autorise le 30 octobre le push, la PR au sommet de la pile et une recette
jetable ; aucune fusion ni mise en production autorisée.

Note de reprise : une seule configuration Django existe désormais à la racine.
Utiliser le Makefile et le README principal ; les anciens lanceurs autonomes
mentionnés dans les notes historiques ci-dessous ont été supprimés.

## 2 novembre 2026 — retrait des parcours historiques `/access/`

Second lot de la transition autonome : suppression complète de
`eures_beta/migration_history`, des anciennes migrations de `candidates` et
`documents`, de l'ancienne migration employeur et des tests de ces historiques.
Le nom `employers.0001_autonomous_schema` et ses opérations restent identiques ;
seul son attribut transitoire `replaces` est retiré. Les anciens labels sortent
de `INSTALLED_APPS`. Le garde-fou bloque une base existante n'ayant pas appliqué
le premier lot. Aucun déploiement effectué par cette PR.

Lot distinct au sommet de la pile, demandé par dejafait : consolidation native
des 36 migrations connectées en `employers.0001_autonomous_schema`. Sur une base
neuve, seules les sept tables métier actuelles sont créées ; un historique
complet est reconnu sans DDL ; un historique partiel conserve son nettoyage et
ses garde-fous. Les anciennes migrations restent pour cette transition, sans
suppression de fichier avant confirmation des environnements. Aucun déploiement
ni accès à la production effectué dans ce lot.
Voir [le protocole de consolidation](docs/AUTONOMOUS_MIGRATIONS.md).

Lot de rangement séparé, demandé après le retrait : les cinq anciens paquets
`accounts`, `offers`, `matching`, `conversations`, `notifications` sont déplacés
sous `eures_beta/migration_history/retired/`, avec leurs tests. Leurs labels et
migrations restent identiques ; aucune nouvelle migration ni modification de
données. Conserver `candidates`, `documents`, `employers` et `occupations`, qui
servent le prototype actuel. Le déploiement est prévu après vérification du
premier lot, sans fusion ni déploiement implicite de ce second lot.
Voir [la transition vers les migrations autonomes](docs/AUTONOMOUS_MIGRATIONS.md).

À la demande de dejafait : supprimer les quatre parcours fictifs, la connexion
sans mot de passe et leur initialisation automatique, en conservant l’accueil
public, le candidat à trois choix et le dépôt employeur trilingue. Migration
ciblée des quatre identités réservées et de leur scénario, sans suppression des
imports employeur actuels. Les douze anciens modèles et tables sont supprimés
après vérification qu'aucune donnée hors scénario ne reste. Les migrations
historiques restent pour la compatibilité des bases ; les anciennes routes
n’existent plus.
Voir [périmètre et effets sur les données](docs/LEGACY_PROTOTYPE_RETIREMENT.md).
Aucune écriture directe en production : les migrations sont testées dans la
base dédiée de la recette et s'appliqueront en production après fusion.

## 30 octobre 2026 — navigation publique canonique

Nettoyage transverse au-dessus du formatage JavaScript : les menus emploient les
routes Django nommées ; les anciennes adresses restent uniquement des redirections
301 de compatibilité avec conservation des paramètres et refus des écritures.
Statistiques, projet et journal disposent de pages d’attente FR/EN/DE publiques,
sans contenu métier simulé ni collecte. Les accès candidat restent protégés.
L’accueil et le tableau de bord ne partagent plus de déclaration de route racine.
Voir [le périmètre](docs/PUBLIC_NAVIGATION.md).

Validation locale : 218 tests PostgreSQL réussis, dont les redirections,
la navigation et les annonces traduites. Aucun modèle ni migration ajouté.
Cette note ne constitue pas une validation de déploiement.

## 30 octobre 2026 — accueil général

Branche `codex/public-home`, initialement depuis #79 puis replacée sur le sommet
#81 (`6d545bc`) pour la publication explicitement demandée par Eric.
Accueil général à `/` et `/forms/eures-beta/`, contenu français repris de la
page de référence consultée, traduit en EN/DE avec gettext. Liens des parcours
locaux et langue conservés ; présentation publique sans collecte ni élargissement
des droits métier. Les chiffres sont repris sans validation statistique.
16 tests ciblés passent sans base de données ; aucun modèle ou migration.
Format Black et djLint, catalogues complets et diff vérifiés. Au navigateur,
aller-retour accueil → employeur → Accueil vérifié en français sur une session
locale vierge (`localhost:9033`). Rendu bureau contrôlé ; pas d’audit mobile
ou WCAG complet effectué. La suite PostgreSQL complète n’a pas été exécutée.
Voir [périmètre et limites](docs/PUBLIC_HOME.md). Push et nouvelle PR autorisés
avec le titre « Mise en place page d'accueil ». Aucune fusion ni mise en production.

## 27 octobre 2026 — fermeture des anciennes sessions hors démo

Suivi de la revue d’Oly sur #50 : `require_identity` refuse désormais les parcours
fictifs hors démo, même avec une session authentifiée ou un ancien `draft_user`.
Les deux régressions ont été reproduites (200 au lieu de 404), puis corrigées.
Neuf tests ciblés et 157 tests PostgreSQL passent ; l’authentification de
`/admin/` reste fonctionnelle. Aucun changement de données ou de protection privée.
Ce correctif permet le démarrage du socle hors démo ; il n’active pas les parcours
de démonstration sur l’environnement permanent. Aucun déploiement vérifié ici.

## 26 octobre 2026 — séparation explicite du mode démonstration

Correctif proposé : démonstration désactivée par défaut, activation locale par
`ME_DEMO_MODE=1`, recettes existantes conservées par `ME_SHARED_DEMO=1`.
Hors démo, l’accueil conserve le socle et les connexions fictives sont fermées ;
le contrôle de démarrage privé qui interdit la démo reste nécessaire.
Ce changement ne fournit pas encore une authentification métier de production.
TDD vérifié localement : six tests de modes exécutés avant correction, huit
assertions en échec, puis tous passent ; 154 tests PostgreSQL réussis après correction.
Aucune migration ni modification de données existantes, aucun déploiement effectué.
## 26 octobre 2026 — un seul accueil employeur traduit

Une PR indépendante remplace les trois accueils par `employer/landing.html`, avec
gettext et catalogues FR/DE. Les 42 textes affichés sont conservés dans les trois
langues ; 146 tests PostgreSQL passent. Les autres pages et les générateurs
restent à migrer : leur suppression complète ne fait pas partie de cette étape.
Voir [le fonctionnement et la suite](docs/EMPLOYER_LANDING_TRANSLATION.md).

## 22 octobre 2026 — lot 4A : lancement simulé

Branche dédiée `codex/employer-search-launch`, base distante du lot 3 `8ca94ce`.
Confirmation explicite recherche/qualification/contact, opérations et événements
durables (migration additive 0008), verrouillage au démarrage confirmé et suspension
des écritures pendant l’incertitude. Vérification simulée sans relancement ;
répétitions et concurrence contrôlées côté serveur. Aucun adaptateur réel ajouté.
108 tests PostgreSQL réussis, dont courses entre collègues et édition/lancement.
Parcours navigateur connexion → confirmation → incertitude → vérification →
verrouillage → duplication vérifié. Recette séparée sur 9021, bases et serveurs
9018/9019/9020 préservés. FR/EN/DE, V2, tableau et CSRF conservés.
Clôture/archivage/réouverture restent à définir. Aucun push, PR nouvelle, fusion
ou déploiement à cette étape. Titre exact à demander avant création d’une PR.
Voir [périmètre et limites](docs/EMPLOYER_SEARCH_LAUNCH.md).

## 22 octobre 2026 — accueil employeur unifié en tableau

À la demande d’Eric, l’accueil et les offres utilisent désormais le même écran.
Bouton d’ajout en tête, établissement unique affiché sous le titre, compte
repliable avec email et déconnexion ; message de vérification email retiré.
Tableau : intitulé/lieu, établissement, état, dernière modification, consultation.
Validation finale : 100 tests PostgreSQL réussis ; contrôles visuels écran large
et étroit, défilement limité au tableau, compte/déconnexion accessibles.
Rattachement et brouillons privés conservés dans des encarts distincts.
Recette 9020 actualisée, aucune modification des recettes 9018/9019 ni des PR.

## 22 octobre 2026 — lot 3 employeur en recette locale

Branche isolée `codex/employer-offer-workspace`, basée sur la tête distante
`ded96d9` de la PR #20 vérifiée en lecture seule. Liste par établissement,
consultation, édition avant recherche et duplication avec lien vers l’original.
Migration additive 0007 : date de recherche et origine de copie. Aucun lancement
de recherche implémenté ; l’état verrouillé de recette est fictif et explicite.
99 tests PostgreSQL passent ; parcours navigateur édition/enregistrement et
duplication d’une offre verrouillée vérifiés. FR/EN/DE, CSRF, droits objet et
révisions conservés. Base et serveur séparés sur 9020, recettes 9018/9019 préservées.
Aucun push, merge ou déploiement. Voir [périmètre et limites](docs/EMPLOYER_OFFER_WORKSPACE.md).

## Ajustement de l’en-tête employeur — 22 octobre 2026

À la demande d’Eric, connexion intégrée à l’en-tête près des langues, avec
« Mon espace employeur » pour une session valide. Pages employeur et V2,
coques de connexion FR/EN/DE ; disposition adaptable et focus clavier visible.
27 tests ciblés passent ; contrôle navigateur du parcours V2 et de l’en-tête
sur écran étroit effectué. Recette 9019 actualisée ; recette intégrée 9018 intacte.


## 22 octobre 2026 — connexion sans offre et ajout connecté

Branche dédiée `codex/employer-connected-add-offer`, basée sur la tête distante
de la PR #19 vérifiée à `c56d5d0`. Le checkout de recette intégrée et son serveur
9018 sont conservés séparément ; aucun de leurs ajustements supplémentaires
n'est repris dans ce diff. Prévisualisation de cette branche : port local 9019,
base PostgreSQL de recette distincte, trois modes locaux activés.

Bouton de connexion FR/EN/DE sur la page employeur et la V2 ; accueil affichant
uniquement les appartenances actives et une action d'ajout, même sans offre.
Le dépôt connecté réserve le brouillon à l'identité courante et conduit directement
au rattachement existant de la PR #19. Le contact conseiller demeure indépendant.
Pour un document ou lien dont la source en session a expiré, un message explicite
demande reconnexion et nouvelle lecture ; les corrections restent dans la page.
Pour la saisie manuelle, une session expirée impose une nouvelle vérification email avant attribution de
l'identité ; le brouillon et son contact sont conservés par session. Aucune
appartenance n'est déduite du contact, d'un nom ou d'un domaine. Plusieurs
appartenances imposent toujours un choix explicite ; une appartenance retirée
ne donne aucun droit. Aucune nouvelle migration.

Validation de cette branche : 88 tests PostgreSQL réussis, dont sept nouveaux
scénarios (sans offre, session valide/contact distinct, choix multiple/refus,
expiration réelle, appartenance absente/révoquée, V2 FR/EN/DE). Parcours navigateur
connexion seule → offre manuelle → contact distinct → établissement réussi sans
nouveau lien. Aucun appel externe. Contrôle visuel limité, sans certification
WCAG. Pas de liste Mes offres ajoutée, invitation ou identification officielle.
Aucune fusion ni aucun déploiement ; PR à créer uniquement après titre fourni par Eric.

## 22 octobre 2026 — rattachement simplifié à un établissement

PR nº 19, basée sur la PR nº 18 : l’offre appartient à un établissement partagé
entre membres habilités, avec créateur conservé. Un seul établissement : nom et
bouton d’enregistrement ; plusieurs : choix explicite ; aucun : nom demandé une
première fois. Aucun autre établissement ne peut être créé depuis cet écran si
une appartenance active existe, y compris par appel direct. Les noms identiques
ne donnent aucun droit sur un établissement existant.

[Parcours et limites](docs/EMPLOYER_COMPANY_OWNERSHIP.md). Invitations et « Mes offres »
restent séparés. Pas d’identification officielle, de modification PDF/logo, ni de
migration de matching dans ce lot. Validation de la version isolée : 81 tests
PostgreSQL passent, dont onze de rattachement ; contrôles Django, migrations,
traductions et diff vérifiés. Aucun merge ni déploiement.

## 22 octobre 2026 — rattachement à un espace entreprise (local)

Lot 2 sur `codex/employer-company-ownership`, issu de la branche du point 1.
Identité individuelle durable, espace entreprise et appartenance explicite active ;
import partagé entre membres, créateur conservé. Réservation du brouillon à la
vérification email, puis choix explicite de l’espace. Aucune recherche par email
contact/domaine. Reconnexion autre navigateur et retrait d’accès testés.
[Parcours, limites et référence Les Emplois](docs/EMPLOYER_COMPANY_OWNERSHIP.md).
Validation : 77 tests PostgreSQL passent ; contrôles Django, migrations et syntaxe
JavaScript réussis. Parcours manuel dans le navigateur et écran de rattachement
vérifiés avec des données fictives. Invitations et « Mes offres » restent séparés ;
aucun merge ni déploiement.

## 22 octobre 2026 — première PR connexion employeur isolée

Connexion email simulée extraite de la copie de recette sur une branche dédiée,
basée sur la PR nº 16. Aucun changement PDF/logo, correctif de boucle ou transfert
de brouillon inclus. [Périmètre et limites](docs/EMPLOYER_EMAIL_LOGIN.md).
Migration additive et accueil minimal FR/EN/DE au design V2. Les lots rattachement,
« Mes offres » et cycle de recrutement restent séparés. Aucun déploiement.
Validation de cette branche : 70 tests PostgreSQL passent, dont neuf de connexion ;
contrôle Django sans erreur, migrations cohérentes et diff vérifié.

# Reprise du prototype Match Europe

## Entrée employeur — 23 octobre 2026

À la demande d’Eric, `/` redirige temporairement (302) vers
`/employer/pages/fr.html`. Les pages EN/DE restent accessibles par
le sélecteur existant. `/access/` conserve les comptes de démonstration et
`/dashboard/` conserve la navigation des quatre rôles après connexion.
Aucun changement graphique, de données ou de service externe.
Validation : 76 tests PostgreSQL passent, dont redirection HTTPS, accueil
FR/EN/DE, accès aux rôles et navigation privée ; `git diff --check` réussi.

## Adaptation de recette — 23 octobre 2026

Autorisation utilisateur distincte : rebaser la PR #2 sur `main`, résoudre les
conflits et ajouter les adaptations dans des commits propres à l’agent, puis
pousser la branche. L’utilisateur ajoutera lui-même le label d’une semaine.
Aucune fusion ni activation du label par l’agent n’est prévue.

Le point d’entrée racine sélectionne désormais les parcours conservés, avec la
sonde PostgreSQL et les statiques du socle. Le mode partagé HTTPS conserve les
protections CSRF/session et initialise seulement une base de démonstration neuve.
Les enregistrements AGLAE et le diagnostic Push sont désactivés. Le lanceur
autonome reste disponible. Voir le README racine pour les commandes et limites.

Vérifications locales : 74 tests du point d’entrée racine et 59 tests du prototype
autonome passent sur PostgreSQL. Migrations et collecte des statiques réussies ;
essai Gunicorn avec rôles fictifs, accès et pages employeur FR/EN/DE à 200,
statiques à 200, santé PostgreSQL à 204, diagnostic Push refusé (404).
Le déploiement de cette adaptation reste à vérifier après le label humain.
## 21 octobre 2026 — parcours employeur avant email

Branche `codex/employer-offer-creation`, basée sur la branche de la PR nº 2. Lecture PDF/URL/texte, vérification et correction avant collecte de l’email et du contact ; demande de lecture portée par le clic sans case supplémentaire. Corrections validées côté serveur lors de l’enregistrement. Textes FR/EN/DE ; mention technique retirée du contact. Les améliorations du lecteur PDF de la PR nº 14 et le changement de logo sont exclus. Mode de recette local sans services externes (`ME_LOCAL_REVIEW_ONLY=1`). Aucun merge ni déploiement autorisé.

La recette précédente avec lecteur amélioré comptait 75 tests ; cette branche indépendante passe 61 tests PostgreSQL, dont les deux nouveaux tests de parcours. Syntaxe des trois scripts JS et diff vérifiés. Les documents et coordonnées de recette sont fictifs et restent hors Git.

## 20 octobre 2026 — lecteur employeur en cours de recette locale

Branche `codex/employer-document-reader` : extraction des champs PDF étendue, exclusion des sections de candidature/offres similaires reconnues, avertissements de contradiction, import d’images et OCR local. Interface FR/EN/DE. Voir [fonctionnement et limites](docs/EMPLOYER_DOCUMENT_READER.md). Les documents de recette restent hors Git. Aucun commit, push, merge ou déploiement demandé : Eric teste d’abord en local. Les vérifications finales de cette modification sont consignées à l’issue du travail.

Vérifications locales : 68 tests PostgreSQL passent ; contrôle Django sans problème ; syntaxe des deux scripts JS et diff vérifiés. Les quatre PDF fournis ont été relus hors Git. OCR Tesseract testé sur les cinq captures et sur une conversion scannée de test. Navigateur : import du PDF ADEM, reprise du brouillon et affichage de l’avertissement 40 h / 20 h vérifiés. Serveur relancé avec `ME_LOCAL_REVIEW_ONLY=1`, après constat qu’un premier essai avait suivi l’ancien circuit AGLAE sandbox. Aucun déploiement effectué.

Suite locale du 20 octobre : séparation des missions/conditions et du profil par rubriques et phrases sources, conservation des nuances souhaitées/exigées, continuité des tâches après les métadonnées de page, exclusion de sections de candidature et d’entreprise reconnues. Vérification sur les quatre PDF et le texte OCR des captures ; 72 tests passent. Réimporter les documents pour obtenir le nouveau tri : les brouillons existants sont préservés.

Publication autorisée par Eric le 20 octobre après recette locale : ajouter ces modifications à la PR de conservation nº 2, demander `dejafait` en reviewer ; ne pas fusionner ni déployer. Vérification finale : 73 tests PostgreSQL passent, y compris l’association de chaque niveau à sa langue (par exemple `French : A1`) et l’isolement des services externes pour la recette. Les documents sources et données locales restent hors Git.

Correction de cette interprétation le même jour : Eric demande une nouvelle PR intitulée « amélioration de l'import des PDF », basée sur `codex/initial-django-prototype` (branche de la PR nº 2), avec `dejafait` en reviewer. La PR nº 2 est restaurée à `51537d0` ; les améliorations sont conservées sur `codex/employer-document-reader-pr2`. Aucun changement direct de `main`, fusion ou déploiement.

## Partage initial — 16 octobre 2026

Cette branche importe une photographie du prototype local, extraite du checkout historique au commit de base `d64f88cd5cbc260c8249cd9ba3842158bc876247` avec ses fichiers de prototype alors non suivis. Aucune réécriture de l’historique du dépôt historique ni copie de sa base locale.

Périmètre : TRANSVERSE, avec les quatre volets EMPLOYEURS, CANDIDATS, CONSEILLERS et ADMIN. Références : [vue d’ensemble](docs/VUE_ENSEMBLE.md), [décisions](docs/DECISIONS.md), [guide de revue](docs/PROTOTYPE_REVIEW.md).

- La V2 employeur est la référence UX acceptée. V1 reste disponible pour comparaison.
- L’import employeur et le modèle `EmployerImport` restent distincts des `Offer` du parcours de matching fictif.
- Le contact entreprise est stocké séparément, avec contrôle d’accès par session et rôle ; attribution conseiller faite par l’admin.
- Les questions de préqualification de la V2 sont momentanément masquées ; aucune exclusion automatique.
- Une conversation métier correspond à un couple candidat–offre après accords et intervention du conseiller.
- Les notifications de test sont isolées. Leur réception a été confirmée manuellement sur le Mac du testeur, mais aucun résultat multi-appareil ou production n’est acquis.

Le dépôt ne contient pas les secrets, données PostgreSQL, abonnements, sessions, documents déposés, sauvegardes locales de versions ni procédures privées d’hébergement.

## À reprendre ensuite

1. Relire les commits par thème ; extraire ensuite de petites PR destinées à une fusion éventuelle.
2. Consolider les templates Django, la génération V2, les traductions et les styles.
3. Raccorder les imports au vrai modèle métier et les notifications au bon participant avec ses droits.
4. Définir authentification de production, révocation, conservation, accords et notices validées.
5. Réaliser audits sécurité, accessibilité et marque ; préparer seulement ensuite un périmètre de recette externe.

Aucun merge ou déploiement n’est autorisé par cette PR. La branche principale doit rester inchangée.

## Vérifications effectuées pour ce partage

Dans ce nouveau clone, avec son propre environnement virtuel et une nouvelle instance PostgreSQL locale :

- Initialisation et migrations `0001` à `0004` : réussies.
- Chargement idempotent des quatre rôles fictifs : réussi.
- `manage.py test journeys --noinput` : **59 tests passent** ; services externes mockés.
- `manage.py check` : aucun problème signalé.
- `makemigrations --check --dry-run` : aucun changement détecté.
- Syntaxe Node des huit fichiers JS/CJS de prévisualisation et JSON : validés.
- HTTP local `/access/`, `/static/app.css`, `/static/bootstrap.min.css` : 200.
- Contrôle des formats de secrets et recherche des secrets locaux connus : aucun dans le jeu de publication.

Les alertes 400/404/409/502 dans la sortie des tests correspondent aux scénarios négatifs attendus. Aucun appel réel au prestataire, géocodeur ou service Push n’a été réalisé pendant cette validation de publication. Une première exécution de tests pendant l’assemblage des commits intermédiaires n’avait pas les routes Push ; la validation ci-dessus porte sur l’état final avec ces routes présentes.

## 28 octobre 2026 — accueil candidat repris sur le main actuel

Branche locale `codex/candidate-landing-main` depuis `3889110`, reprise ciblée
de l’écran validé le 26 octobre. Route `/candidate/?lang=fr`, ancien lien de
navigation conservé ; templates et statiques Django, textes candidat gettext
FR/EN/DE, protections hors démo conservées. Choix et connexion simulés uniquement.
165 tests PostgreSQL et contrôles de qualité réussis ; quatre tests candidat
repassés après raccordement gettext. Navigation FR/EN/DE et activation clavier
vérifiées dans le navigateur local. Aucun changement de modèle ou de service
externe, aucune publication. Voir [périmètre et limites](docs/CANDIDATE_LANDING.md).

### Consolidation dans la PR #63

Après déplacement au-dessus de la pile métier/traductions : un seul template
gettext pour l’accueil candidat et son en-tête, ses statiques et tests dans
`candidates`, contrôle d’accès transverse conservant les mêmes restrictions.
Retrait du générateur candidat et de son dictionnaire JSON désormais redondants.
187 tests PostgreSQL réussis, compilation gettext, Black, contrôles Django et
collecte statique réussis. Textes, liens et attributs rendus FR/EN/DE comparés à
la version précédente sans différence. Les parcours restent simulés ; aucune
fusion ni mise en production effectuée pour cette consolidation.

## 28 octobre 2026 — finalisation de la pile métier et gettext

Suite de la PR #63 : format HTML djLint dans une PR indépendante, gettext pour
les derniers messages navigateur et le diagnostic Push, retrait des générateurs.
Applications comptes, employeurs/imports et matching extraites ; les derniers
formulaires et utilitaires sont rangés dans leur domaine. `journeys` n’est plus
un dossier métier : `migration_history` conserve ses 18 migrations et son label
technique, sans modèle actif. Tables physiques et données conservées.

Vérifications locales de cette série : tests PostgreSQL des parcours et des
migrations aller-retour, contrôles Django, Black, djLint et catalogues FR/DE.
Aucune fusion ni mise en production n’est effectuée par cette série. L’accueil
candidat garde ses trois choix simulés, sans collecte ni parcours suivant.

## 29 octobre 2026 — catalogue partagé adapté au sommet #74

Branche `codex/occupation-catalog-local` depuis #74 (`8abbde2`). Reprise ciblée
dans `eures_beta/occupations`, sans modèle ni migration : catalogue ESCO 1.2.1
FR/EN/DE (3 039 concepts), ROME 26M10 (1 923 fiches, 14 330 appellations),
table officielle de 13 120 liens. Sources et lacunes versionnées, aucune API
à l’usage. Recherche et rapprochements ancrés sur le meilleur résultat repris.
Pas d’import CV, page d’essai candidat ou générateur réintroduit.
199 tests PostgreSQL réussis avec réseau externe interdit ; 31 recherches
multilingues et reconstruction identique des deux gzip/manifeste contrôlées.
Catalogue indépendant du futur raccordement employeur. Aucune publication,
fusion ou mise en production à cette étape.
Voir [sources et maintenance](docs/OCCUPATION_CATALOG_MAINTENANCE.md).

## 29 octobre 2026 — raccordement employeur adapté au train

Branche `codex/employer-occupation-selection` au-dessus de
`codex/occupation-catalog-local` (PR #76, elle-même sur #74). Reprise ciblée dans
`employers` et `occupations`, sans copie de l’application `journeys`, générateurs
ou changements candidat. Widget FR/EN/DE depuis un fragment gettext inclus dans
le template unique. Sélections et références validées serveur, conservées dans
le JSON de l’import avec les droits et révisions existants.
202 tests PostgreSQL réussis avec réseau externe bloqué ; Black, djLint, gettext,
check et absence de migrations nouvelles vérifiés. Recette distincte : sauvegarde
de deux descriptions pour un boulanger, réouverture avec cases cochées, effacement
des choix après changement de titre vérifiés dans le navigateur. Aucune donnée
de la recette historique modifiée. Aucun nouveau contrat externe, aucune fusion
ou mise en production. Éditeur connecté historique sans widget et import CV exclus.
Voir [fonctionnement et limites](docs/EMPLOYER_OCCUPATIONS.md).

## 29 octobre 2026 — correction recherche après import d’un intitulé enrichi

Bug reproduit : les suffixes genre/contrat/horaires bloquaient toute correspondance.
Nettoyage uniquement pour la recherche, titre utilisateur inchangé. Pour les titres
génériques, priorité aux libellés ESCO multilingues explicites présents dans le
contexte de l’offre ; les titres exacts restent prioritaires. Requête du widget
en POST JSON/CSRF pour ne pas mettre les missions dans l’URL. Aucun réseau externe.
203 tests PostgreSQL réussis sans réseau externe, régression et CSRF inclus.
PDF fourni relu dans le navigateur : une description pertinente selon le libellé
de métier de la source apparaît sans être cochée, automatiquement puis au clic.
Document conservé hors dépôt et hors fixtures ; aucune offre réelle enregistrée.
Correction ajoutée à la branche de la PR #77, sans rebase ni changement de #76.

## 29 octobre 2026 — essai métier indépendant avec recherche pendant la saisie

À la demande d’Eric, champ métier indépendant de l’intitulé de l’offre et recherche
progressive (300 ms, à partir de deux caractères, annulation des réponses anciennes).
Option de recherche directe par code ROME, code ESCO, UUID ou URI ; contrôle local
exact et associations multiples explicites. Titre extrait indiqué comme repéré,
titre manuel étiqueté distinctement. Choix conservés entre recherches et séparés
visuellement des nouvelles propositions. FR/EN/DE, mêmes droits et CSRF.
204 tests PostgreSQL passent avec réseau externe bloqué, puis 38 ciblés repassés
après textes ; essais navigateur de recherche indépendante, saisie progressive
et code D1102 réussis. Essai local sur 9031 et branche
`codex/occupation-picker-live-trial`, hors train publié en attente du retour UX
d’Eric. PR #77 non modifiée par cet essai ; aucun push/fusion/déploiement.

## 29 octobre 2026 — suppression du doublon d’intitulé dans l’essai local

Sur retour d’Eric : recherche initiale depuis l’intitulé et propositions directes.
Le champ de recherche n’est plus prérempli ni visible au départ ; il apparaît vide
avec message d’absence de correspondance, ou à la demande si aucune proposition
ne convient. Recherche progressive et alternative ESCO/ROME conservées en recours.
Les deux branches d’affichage ont été vérifiées dans le navigateur ; pas de
changement d’API, modèle ou permissions. FR/EN/DE compilés et vérifiés, JS et
format HTML contrôlés. Reste sur la branche locale d’essai hors train publié.

### Visibilité de l’action de recours

Après retour UX d’Eric : action « Aucune de ces descriptions ne convient »
déplacée au-dessus des cartes, bouton pleine largeur avec bordure et fond
contrastés. Clic vérifié : ouvre le champ manuel vide et y place le focus.
Syntaxe JS et diff contrôlés ; modification de présentation uniquement, locale.

### Position finale du bouton de recours (retour Eric)

Design contrasté et pleine largeur conservé ; bouton replacé après les cartes
de métiers, conformément au retour suivant d’Eric. Essai local uniquement.

### Champ de recours unique : intitulé, ROME ou ESCO

Sur demande d’Eric, suppression du champ de référence séparé. Le même champ
accepte un intitulé, un code ROME ou une référence ESCO ; détection serveur
automatique des codes/UUID/URI, saisie progressive inchangée. 38 tests ciblés
PostgreSQL hors réseau externe passent, dont toutes les références testées sans
mode explicite. Traductions FR/EN/DE, JS et HTML contrôlés. Code D1102 testé au
navigateur dans le champ unique. Essai local seulement, hors train publié.

### Message précis d’échec automatique après lecture d’un document

Distinction du titre issu d’un document et du titre manuel pour l’échec initial.
Message FR : « L’intitulé déduit de votre fiche de poste ne nous a pas permis de
trouver une correspondance automatiquement », suivi directement du champ mixte
vide ; pas de textarea personnel initial. Traductions FR/EN/DE compilées et
contrôlées. Version des fichiers widget/review/CSS dans le template actualisée
pour éviter la réutilisation de statiques anciens au rechargement. Comparaison
HTTP/source confirme le bon JS sur 9031 ; réponse HTML réelle relue avec le
message attendu et l’URL de statique actualisée. Contrôles JS/HTML/diff réussis.
Essai local seulement ; ancien écran déjà chargé à actualiser pour tester.

### Épuration visuelle de la recherche métier

Retrait du bouton Trouver des descriptions, du titre Précisez le métier proposé
et des paragraphes répétés. Seuls restent le label Rechercher un métier, un
exemple en placeholder, l’aide courte Intitulé ou code ROME/ESCO, puis les cartes.
Message d’échec automatique préservé lorsque nécessaire ; nombre de résultats
annoncé aux lecteurs d’écran sans ajout de texte visuel. Recherche au fil de la
saisie vérifiée navigateur avec boul ; syntaxe JS, HTML, gettext FR/EN/DE et diff
contrôlés. Essai toujours local, sans push ni changement des PR publiées.

## 29 octobre 2026 — publication autorisée de la recherche métier améliorée

Eric valide la publication des itérations UX dans une nouvelle PR intitulée
« amélioration de la recherche de métiers », basée sur le sommet revalidé #77
(`codex/employer-occupation-selection`). Champ mixte progressif en recours,
intitulé de l’offre conservé, bouton après les cartes et aide espacée du focus.
38 tests ciblés PostgreSQL passent à nouveau, réseau externe bloqué ; contrôles
Black, JavaScript, templates et diff réussis. Relecture à demander à dejafait.
Cette autorisation porte sur push/PR, sans fusion ni déploiement.

## 29 octobre 2026 — essai local de relecture employeur en cinq étapes

Branche `codex/employer-review-steps-trial`, basée sur la livraison #78, non publiée.
Réorganisation des contrôles existants : poste, conditions, profil, mobilité,
récapitulatif. Navigation précédent/continuer, focus des titres, validation des
champs de l’étape et retour Modifier depuis le récapitulatif. Les champs et le
contrat de sauvegarde restent inchangés ; aucune migration ni nouvel appel externe.
Textes de navigation FR/EN/DE compilés. Le contact reste un formulaire enregistré
séparément, visible à la dernière étape. Pas d’autosauvegarde : bouton brouillon
existant conservé sur chaque écran. Recette avec données fictives : cinq étapes,
retour depuis la synthèse, réponse conservée, sauvegarde et réouverture réussies.
38 tests catalogue/imports repassés ; syntaxe JS, templates et diff contrôlés.
Les réponses guidées et nouvelles questions proposées restent un lot ultérieur.

### Conditions guidées — essai local

Rémunération : montant fixe ou fourchette, devise, brut/net, période. Durée du
travail : heures hebdomadaires fixes ou variables. Prise de poste : immédiate,
date précise ou flexible. Les contraintes horaires restent dans les conditions
de travail, avec précision facultative. Sources importées conservées explicitement
sans interprétation automatique ; champs produits par cette interface restaurés
dans la même langue après reprise. Pour cet essai UX, le contrat existant reste\;textuel : valeurs guidées sérialisées dans les clarifications, pas encore un
schéma métier structuré côté serveur. Un changement de langue conserve le texte
s’il ne reconnaît pas le format. Bornes positives et fourchette ordonnée contrôlées
dans le navigateur. Recette fictive : sauvegarde/reprise 2400 EUR brut mensuel,
35 heures, dès que possible ; fourchette inversée refusée, valide acceptée.
FR/EN/DE compilés ; JS, format HTML et diff contrôlés. Aucun push ni déploiement.

### Progression obligatoire avant enregistrement

Sur demande d’Eric, retrait du bouton brouillon/enregistrer des quatre étapes
intermédiaires. Seule l’action Continuer accompagne le retour Précédent ;
enregistrement disponible au récapitulatif. Réponses attendues contrôlées
au navigateur, y compris groupes conditions, permis et mobilité. Les choix
À préciser demeurent des réponses explicites ; aucune sélection par défaut
dans les nouveaux modes guidés vides. Précisions facultatives conservées.
Recette : absence de réponse aux conditions bloque, sélection explicite autorise
la suite ; absence de bouton enregistrer vérifiée. Ce lot reste une recette UX
locale ; le contrat serveur historique n’est pas durci dans ce changement.

### Langues et niveaux expliqués

Module local : français, allemand, anglais, luxembourgeois et une autre langue
facultative. Pas nécessaire ou A1–C2 avec descriptions pratiques FR/EN/DE,
inspirées de l’échelle globale du Conseil de l’Europe (repères, pas certification).
Préremplissage seulement pour un couple langue/niveau explicite reconnu, exemple
French: A1 ; aucune déduction depuis langue de rédaction ou « bon niveau ».
Texte ambigu conservé comme source ; choix de chaque langue principale exigé.
Les réponses restent sérialisées dans la clarification existante pour l’essai UX.
Recette fictive : préremplissage French: A1, autres langues Pas nécessaire,
sauvegarde finale et reprise avec choix conservés. Contrôles JS/HTML/gettext.
Aucune publication ; validation du contrat de données structuré reste ultérieure.
Référence : https://www.coe.int/en/web/common-European-framework-reference-languages/table-1-cefr-3.3-common-reference-levels-global-scale

### Condition horaires avec coupure

Ajout du choix split (Horaires avec coupure) aux conditions employeur, aux
libellés du récapitulatif et à l’éditeur historique pour éviter sa perte.
FR/EN/DE compilés ; 38 tests ciblés passent, dont sauvegarde/reprise avec split.
Case et exclusion mutuelle avec Aucune condition particulière vérifiées navigateur.
Modification locale, sans publication.

### Langues ajoutées à la demande

Liste fixe retirée. Seules les langues explicitement requises apparaissent ;
recherche locale dans les codes ISO 639-1 avec libellés Intl.DisplayNames FR/EN/DE,
suggestions limitées à huit et exclusion des doublons. Ajout, niveau A1–C2 expliqué,
retrait et choix explicite Aucune exigence linguistique particulière. Ni niveau
ni langue déduits d’une absence de donnée ; texte source ambigu préservé.
Compatibilité avec les anciens choix Pas nécessaire ; seuls les positifs sont
affichés. Quatre réponses négatives explicites anciennes restent compatibles.
Recette fictive : ajout anglais B1, sauvegarde finale et reprise français A1/anglais
B1 ; retrait des deux bloque la progression, puis choix sans exigence autorise
la suite. JS, gettext FR/EN/DE et format template contrôlés. Essai local non publié,
contrat de persistance textuel inchangé.

## 29 octobre 2026 — publication autorisée du parcours séquencé

Eric autorise push et nouvelle PR au sommet revalidé #78, sous le titre exact
« améliorations et séquençage du parcours de dépôt d'offre ». Le lot regroupe
les cinq étapes, conditions guidées, coupure et langues à la demande, documentés
dans docs/EMPLOYER_REVIEW_STEPS.md. Suite complète de 204 tests PostgreSQL
repassée avec réseau externe interdit ; Black, neuf templates employeur, syntaxe
des trois nouveaux modules JavaScript et diff contrôlés. Les limites de stockage
textuel et de contrôle de complétude au navigateur sont explicites.
Aucune fusion ni déploiement autorisés.

## 30 octobre 2026 — entrée vers le parcours enrichi

La recette #80 contient bien les commits #76–79, mais l’accueil et l’espace
employeur pointaient toujours vers import-v2, qui ne porte pas les évolutions
ESCO/intitulé et cinq étapes. Les entrées accueil, ajout d’offre et reprise
pointent désormais vers import, qui contient ces évolutions. La V2 reste
accessible par son URL historique. Aucun transfert ni duplication de données.

## 30 octobre 2026 — allègement de la relecture

À la demande d’Eric, retrait du bloc global « Informations à vérifier » au-dessus
de la fiche, sans modifier les valeurs extraites ni les contrôles de validation.
La mention de lecture conserve l’extraction locale et l’absence d’IA générative,
mais retire la référence au prestataire. Progression en cinq colonnes avec
libellés courts, compteur étape/total et barre ; sur petit écran, les numéros et
le titre courant restent affichés. FR/EN/DE, aria-current et navigation
Précédent/Continuer conservés. Tests de pages trilingues et gettext réussis,
syntaxe JavaScript contrôlée et rendu bureau local inspecté.

## 30 octobre 2026 — essai ESCO et ROME indépendants

Recherche directe ROME par appellation ou code, distincte des descriptions ESCO,
et présentation en deux listes. ROME demeure en français, avec absence de
descriptions détaillées signalée. Choix explicites, stockage séparé dans le JSON
existant et reconstruction serveur ; anciennes sélections compatibles. Aucun
changement de matching ni d’appel externe. Voir docs/EMPLOYER_OCCUPATIONS.md.

## 30 octobre 2026 — reprise après échec de recherche

Capture Eric : erreur de chargement au premier affichage après import. La même
recherche réussit après relance dans son onglet, sans changement final de titre
ni sauvegarde ; origine du premier échec non reproduite. Ajout d’un bouton de
relance automatique et message distinct d’une absence de résultats, avec recours
manuel conservé. Aucun résultat fictif substitué à une erreur réseau.

## 30 octobre 2026 — visibilité du message de recherche

À la demande d’Eric, message d’échec et bouton de relance regroupés dans un
encadré contrasté avant le champ de recherche manuelle. Le message conserve son
rôle d’alerte et est relié au champ par aria-describedby. Bloc masqué lorsqu’il
est vide. Aucun changement de recherche, de sélection ou de sauvegarde.

## 2 novembre 2026 — journal public, préparation locale

Branche `codex/project-journal`, au-dessus de `codex/project-page` (#93).
Le journal remplace l’écran d’attente de `/journal/` ; les entrées existantes
des menus conservent cette route. Quinze entrées : treize historiques et deux
jalons sur l’engagement des trois structures en septembre et l’arrivée des
collègues début octobre. Priorité à leur accueil et prise en main du projet,
sans campagne d’acquisition pendant cette période. Pas de bilan chiffré au
2 novembre. Contenu gettext FR/EN/DE, cadre public et logos existants conservés.
Sommaire avec ancres et cartes chronologiques, styles adaptés aux petits écrans.
`make test TEST_ARGS='-k journal -k public_navigation -k project'` vérifie les jalons, langues, liens et méthodes HTTP.
Version et design validés par Eric le 2 novembre ; publication GitHub autorisée
sous le titre « journal du projet », au sommet de la pile. Aucune fusion ni
mise en production autorisée.

Vérifications locales du 2 novembre : neuf tests ciblés réussis via
`make test TEST_ARGS='-k journal -k public_navigation -k project'`, contrôles Black, djLint, disposition des templates et
traductions réussis. Rendu navigateur contrôlé à 1440 et 390 px sans débordement
horizontal ; lien du sommaire vérifié. Ces tests de page ne nécessitent pas de
connexion à une base ; aucune validation d’intégration PostgreSQL revendiquée.
Base distante #93 vérifiée au commit `7c618603e45752c966dae6ac34cf0e43134d1263`.
## 2 novembre 2026 — rafraîchissement après suppression des archives

La PR comptes uniques est rebasée sur le main sans `migration_history`.
Sa migration dépend directement du schéma autonome. L'essai de mise à niveau
construit ce schéma avec le chargeur Django normal, sans recréer d'archives.
Un garde-fou vérifie le marqueur autonome avant la première bascule utilisateur.
Les tests des anciens modèles sont retirés avec leurs sources ; les tests du
schéma actuel et de conservation des données restent actifs. Aucun changement
des choix métier conseiller/employeur, aucune fusion de cette PR.

## 2 novembre 2026 — connexion par lien magique (PR dédiée)

Ajout de users/views.py, du formulaire public et de django-sesame 3.2.5. Bouton
commun aux pages publiques, en FR/EN/DE ; seuls les comptes actifs préexistants
peuvent recevoir un lien. Pas de backend de connexion par mot de passe. Liens
de 15 minutes à usage unique, confirmation POST/CSRF et session glissante de
30 jours. Compteurs anti-abus PostgreSQL dans une migration additive.
Le SMTP reste désactivé et annoncé comme tel, conformément à la demande de
dejafait : recette visuelle maintenant, raccordement Brevo distinct ensuite.
Suite complète : 229 tests PostgreSQL passent. Voir docs/MAGIC_LOGIN.md pour
les réglages, les limites de temporisation SMTP et les journaux à protéger.
Aucune fusion ni modification de production dans ce lot.

## 2 novembre 2026 — correction CSRF de la connexion HTTPS

403 reproduit dans Chrome lors de la confirmation du lien magique. La politique
no-referrer appliquée au formulaire provoquait une origine null, rejetée par
Django. Test de régression ajouté et constaté rouge (1 échec sur 230), puis
correction : same-origin pour les pages nettoyées, no-referrer conservé sur la
redirection portant le jeton. Les 230 tests PostgreSQL passent après correction ;
une origine étrangère reste rejetée. Aucun contournement CSRF ni changement de
secret, de durée du lien ou de permission.

## Administration des comptes — 2 novembre 2026

Proposition non déployée : droits de création et consultation des conseillers
pour les conseillers actifs `is_staff`, réconciliés après chaque `migrate`
complet. Aucun droit de modification, suppression ou attribution de privilèges
pour ces gestionnaires. Voir [la politique](docs/ADMIN_PERMISSIONS.md).
Validation locale : 215 tests PostgreSQL et contrôle de transition utilisateurs
réussis. L'authentification par lien magique et les invitations restent séparées.

## 2 novembre 2026 — page Mon compte

PR dédiée : fiche privée en lecture seule avec rôle, e-mail, nom facultatif et
date de création. Navigation commune Mon compte / Me déconnecter ; lien Admin
uniquement pour is_staff, vers Django. FR/EN/DE et layout public conservés.
Tests de confidentialité, refus des modifications, comptes inactifs et navigation
par rôle ajoutés ; aucune migration ni modification des droits.
Voir docs/ACCOUNT_PAGES.md.

## 2 novembre 2026 — tableau de bord commun

PR empilée sur Mon compte : arrivée après lien magique sur /accounts/dashboard/
et bouton Tableau de bord pour tous les comptes connectés. Page privée commune
annoncée en construction en FR/EN/DE, sans liste métier ni nouveaux droits.
La page de connexion redirige aussi une session déjà ouverte vers ce tableau.
Validation locale : 267 tests PostgreSQL passent, dont le parcours HTTPS/CSRF
pour employeur, conseiller et conseiller staff.


## 2 novembre 2026 — parcours candidat local

Branche `codex/candidate-local-journey` créée dans la copie courante, qui ne reste donc plus une référence détachée inchangée. Parcours avec/sans CV, profil commun en cinq étapes et récapitulatif ; interface FR/EN/DE. Lecture brute PDF/image partagée dans `documents`, brouillon de session uniquement, sans migration ni changement employeur. 231 tests PostgreSQL passent, dont 10 nouveaux. Recette : `make candidate-run`. Voir [périmètre, conservation et limites](docs/CANDIDATE_JOURNEY.md). Aucun push, fusion ou déploiement.


### Ajustement local candidat — choix guidés et métiers

Recherche ESCO/ROME indépendante raccordée à l’API locale existante, sélection multiple conservée et validée côté serveur, relecture avec libellés canoniques. Pays, langues, permis, disponibilité, mobilité, contrats, quotité, conditions et salaire guidés. Contrôles serveur et détails conditionnels. 235 tests PostgreSQL réussis, recette navigateur jusqu’au récapitulatif. Voir `docs/CANDIDATE_JOURNEY.md`. Aucun changement employeur, migration, push ou déploiement.


### Correction locale — reprise sans CV

Le lien « Commencer sans CV » ouvre toujours le projet (étape 2), même avec un brouillon déjà avancé. La condition précédente ne sautait le dépôt que lors du premier démarrage. Progression et réponses existantes conservées ; test de reprise FR/EN/DE ajouté.


### Horaires candidat — module historique

À la demande d’Eric, reprise locale du choix horaires variés/contraintes puis grille hebdomadaire matin, après-midi, soir, nuit, avec adaptation mobile. Source historique locale consultée, site FT inaccessible en lecture directe. Noms métier, validation serveur, conservation en session et relecture. Aucun changement distant.


## 2 novembre 2026 — candidat sans CV ni historique professionnel

Décision d’Eric : reprendre l’esprit du questionnaire historique FT et garder ESCO/ROME ; retirer import CV, expériences, formations/diplômes et compétences. Quatre étapes, bouton de démarrage unique. Choix historiques de trajet et transports ajoutés conditionnellement à mobilité/langues ; horaires hebdomadaires conservés. Retrait du lecteur introduit uniquement pour l’essai CV et refus serveur des fichiers. Nettoyage des champs retirés à la reprise des anciennes sessions, projet/préférences conservés pour relecture. Aucun changement du lecteur employeur, du modèle ou du matching. Voir `docs/CANDIDATE_JOURNEY.md`.


### Langues candidat — module partagé

Module employeur réutilisé pour ajout/recherche/retrait de langues et niveaux A1–C2 expliqués. Textes candidat, déclaration structurée et validation serveur, anciens niveaux repris sans équivalence inventée. 235 tests PostgreSQL passent. Recette navigateur recherche portugais, ajout, B1 et retrait sans enregistrement de la langue d’essai. Aucun changement du format des données employeur ou déploiement.


### Conditions candidat — précochages et incohérences

Précochages journée/soirée-nuit/week-end depuis la grille, explication visible et priorité aux corrections manuelles. Option de disponibilités exclusives, alerte immédiate et validation serveur si aucune intersection avec une condition acceptée. Référence week-end distincte des jours fériés. Recette navigateur dans une session localhost distincte, sans modifier le brouillon utilisateur : propositions, correction manuelle et alerte vérifiées. Tests ciblés : 23 réussis. Aucun déploiement.


## Publication du parcours candidat — 2 novembre 2026

Sur demande d’Eric, préparation de la PR « parcours candidat » au sommet courant. Aucune PR encore ouverte lors du contrôle : base `main`, actualisée à `1c0ffba`. Rebase ciblé résolu en conservant la suppression des anciens modèles/prototypes et les nouveaux liens de connexion ; aucune réintroduction d’inscription autonome.

305 tests PostgreSQL passent sur ce socle ; contrôles Django, absence de nouvelle migration, format Python/templates/JavaScript et traductions réussis. Les comptes et migrations du main nécessitent une nouvelle base locale de recette distincte : ancienne base conservée, seules sessions recopiées pour préserver les brouillons. Aucune donnée externe, fusion ou action de déploiement. Le parcours candidat demeure protégé comme démonstration.
# E-mails réservés à la production

Backend SMTP commun exigeant `DJANGO_ENVIRONMENT=production` et
`EMAIL_DELIVERY_ENABLED=1`. Local et recettes restent sans envoi par défaut.
PR indépendante du parcours candidat. Tests sans e-mail réel ; configuration
du prestataire exclusivement privée. Voir [connexion](docs/MAGIC_LOGIN.md).
## 3 novembre 2026 — filtres de l’administration

PR dédiée au-dessus de l’admin en lecture seule : bouton afficher/masquer le
panneau de filtres, préférence navigateur mémorisée, FR/EN/DE. Les filtres actifs
et permissions sont conservés ; sans JavaScript le panneau reste visible.
Pas de modification responsive, des adresses e-mail ou de la barre gauche.
# 2026-11-03 — Comptes fictifs en local/recette

Sélecteur traduit et peuplement idempotent : voir [TEST_ACCOUNTS](docs/TEST_ACCOUNTS.md).
Trois rôles fixes et deux offres ; aucun modèle/migration nouveau. La production
doit rester désactivée. `make test TESTS=tests.users.test_test_accounts` couvre les garde-fous et la CSRF.

## 3 novembre 2026 — compteurs de modèles sur l’accueil admin

PR dédiée : nombres d’enregistrements à la demande, désactivés par défaut,
entre parenthèses à côté des modèles accessibles. Querysets et permissions admin
respectés ; aucune écriture en base ou préférence persistante. FR/EN/DE.
## 3 novembre 2026 — navigation admin repliée par défaut

Second commit de la PR des compteurs : navigation gauche initialisée fermée,
bouton et mémorisation natifs Django conservés. Les préférences déjà explicites
restent respectées. Aucun changement de l’affichage par défaut des filtres droits.

# 2026-11-03 — Tableau employeur en consultation

`employers/dashboard.py` affiche les offres accessibles via les adhésions actives
et les brouillons du compte, sans brouillons anonymes ni déduction par e-mail.
Liste paginée FR/EN/DE, aucune action d’écriture ajoutée, modèles inchangés.
Voir [ACCOUNT_PAGES](docs/ACCOUNT_PAGES.md) et les tests métier du tableau.
# 2026-11-03 — Import employeur authentifié

Pages d’import et API réservées au rôle employeur actif. Nouvelle page d’accès,
reprise après lien magique via chemins fixes, offre enregistrée au compte puis
retour au tableau. Aucun nouveau modèle ni inscription automatique. Sources
préparées liées au compte, création anonyme fermée ; voir
[EMPLOYER_IMPORT_ACCESS](docs/EMPLOYER_IMPORT_ACCESS.md).

## Renommage des modèles employeur — 3 novembre 2026

PR dédiée sur main : `Company`, `CompanyMembership`, `JobOffer`, références
runtime/admin/tests/documentation adaptées. Migration d’état sans DDL sur les
tables métier ; métadonnées et permissions renommées en conservant leurs IDs.
Test PostgreSQL d’aller-retour avec objets liés, données JSON, groupes, droits
directs et journal admin. Aucun changement des six autres noms de modèles,
des routes métier, des données de production ou déploiement dans cette tâche.
## 3 novembre 2026 — accès à l’import depuis le tableau employeur

Bouton d’import partagé avec la page publique employeur, langue conservée et
visible même avec une liste vide. Texte contradictoire corrigé en FR/EN/DE.
Aucune nouvelle permission, donnée, migration ou API ; parcours existant réutilisé.

## 3 novembre 2026 — recherche métier : attente bornée et repli manuel

Le navigateur pouvait rester sur « Finding descriptions… » sans délai limite,
avec la description personnelle cachée même après une erreur HTTP. Deux tests
JavaScript sur le module réel reproduisent ces défauts avant correctif ; le cas
nominal reste couvert. Attente bornée à 15 s, réponse JSON incluse, reprise et
saisie manuelle accessibles sans inventer de référence métier. L’API de production
répondait à un contrôle ponctuel : cause réseau exacte de l’onglet bloqué non
établie. Aucun changement de modèle, de données métier ni de permissions.
Validation : 354 tests PostgreSQL et trois tests JavaScript réussis, contrôles
Django/migrations, Python, HTML, JavaScript et traductions réussis.

# 2026-11-03 — Performance du nettoyage des intitulés métiers

Défaut exponentiel reproduit dans `occupations.catalog.search_title` sur une
parenthèse mal formée courte. Test isolé rouge puis correctif sans quantificateurs
imbriqués ; classements, données et intitulés stockés conservés. Mesures et limites
dans [OCCUPATION_SEARCH_PERFORMANCE](docs/OCCUPATION_SEARCH_PERFORMANCE.md).
Commandes : `make test TESTS=tests.occupations.test_search_performance`, `make occupations-benchmark`.
# 4 novembre 2026 — stockage structuré candidat

Préparation au-dessus de la PR #127 (`4892caa`) : modèle `CandidateProfile`,
migration `candidates.0001_initial`, fiche unique par compte candidat,
contrôle de rôle applicatif/PostgreSQL et administration limitée aux métadonnées.
Le questionnaire conserve son brouillon de session et ne crée aucune fiche.
Voir [contrat, champs et limites](docs/CANDIDATE_PROFILE_STORAGE.md).

Validation effectuée dans un worktree et une base locale dédiés : 373 tests
PostgreSQL réussis, migration neuve appliquée, aller/retour testé, contrôles
Django/migrations, format Python et traductions réussis. Les tests de migration
du rôle restaurent désormais aussi leurs migrations dépendantes.
Les choix de conservation et le raccordement avec vérification email restent
à traiter avant toute collecte réelle. Aucun déploiement ni fusion effectué.

# 6 novembre 2026 — migration candidat après retrait du prototype

Le registre historique peut contenir `candidates.0001_initial` alors que les
tables anciennes ont été retirées. Le nom réutilisé dans le nouveau stockage
fait alors sauter sa création. Test de régression constaté rouge : table
`candidates_candidateprofile` absente malgré le marqueur initial.
La migration corrective `0002_ensure_candidate_profile_schema` crée seulement
la table manquante, avec unicité, clé étrangère et contrôle PostgreSQL du rôle.
Une table déjà présente et ses profils sont conservés, y compris lors du
retrait du seul correctif. Aucun ancien modèle ni compte fictif restauré.
Validation locale : 376 tests PostgreSQL, transition utilisateurs, contrôles
Django/migrations, Python, HTML, JavaScript et traductions réussis.

# 5 novembre 2026 — validation de la pile #127 / #128 / #129

Revue isolée au-dessus de #129 : 386 tests réussis avant correction. Les deux
échecs signalés sont reproductibles avec `ME_LOCAL_REVIEW_ONLY=1` hérité ; les
tests d'intégration fixent maintenant leur mode explicitement. Correction
supplémentaire : prolongation du brouillon candidat par POST protégé et
confirmation JSON explicite, refus après expiration, message d'échec FR/EN/DE
sans promesse de conservation. Trois tests serveur et quatre tests JavaScript
ajoutés ; 389 tests PostgreSQL passent, y compris avec ce réglage local hérité.
Migrations sur base vide et contrôles qualité réussis. Workflow PostgreSQL
étendu aux PR empilées ; aucun résultat distant revendiqué pour ce changement.
Le diagnostic `make users-upgrade-test` exclut désormais de sa reconstruction
historique les migrations dépendant du compte actuel, dont le profil candidat ;
la transition complète et sa répétition passent après correction.
Voir `docs/STACK_VALIDATION_20261105.md` pour les limites et la recette manuelle
restante. Aucune fusion ni opération de production.

# 5 novembre 2026 — notice commune de protection des données

Reprise dans Django du cadre Flask : page publique FR/EN/DE `/privacy/`,
durées candidats/employeurs 12 mois, rapprochements 24 mois, invitations sans
réponse et journaux 6 mois, statistiques agrégées/anonymisées seulement pour
une conservation plus longue. Liens depuis les parcours publics, candidats et
employeurs, imports et accès employeur. Notice antérieure conservée et reliée.
Distinction entre brouillon temporaire (30 minutes sans activité), profil durable
et purge technique. Aucun modèle, migration, collecte réelle ou effacement
automatique ajouté. Voir `docs/DATA_PROTECTION.md` pour la provenance et les
points à préciser lors du raccordement P1. Aucune fusion effectuée par l'agent.

## 5 novembre 2026 — mentions visibles du prestataire

Retrait demandé par Eric des deux mentions du prestataire dans les textes du
contact et de la notice historique employeur, en FR/EN/DE. Modification de
libellés uniquement, sans changement des intégrations, droits ou données.
Validation : 147 tests PostgreSQL employeur réussis, catalogues vérifiés et
compilés. Aucune fusion ni opération de déploiement.

## 6 novembre 2026 — contact pour les invitations employeurs

Le contact par défaut est désormais celui du bandeau existant : Eric Barthélémy.
L’encart FR/EN/DE dirige vers son email et non vers l’annuaire général EURES.
La destination configurable est conservée sans ajout automatique de langue.
Aucune modification des droits, modèles ou données.

## 6 novembre 2026 — textes de la notice dans le template

Suppression du module data_protection.py : textes et tableau repris dans le
template avec gettext ; routes et structure des vues inchangées.

La PR #132 est isolée de la pile à la demande de dejafait. La notice ne doit donc
pas importer son module d'inscription, ni annoncer un enregistrement candidat
absent de cette branche. Les tests de notice ont reproduit l'import manquant
avant suppression de ce couplage ; le texte reste celui du questionnaire en
session sans création de compte. Le code et la branche #132 ne sont pas modifiés.

## 9 novembre 2026 — notice #149 isolée sur main

À la demande de dejafait, la PR #149 est extraite de la pile pour une livraison
indépendante. Les textes gettext conservent le comportement de main : questionnaire
en session, sans création de compte candidat, et expiration après 30 minutes.
Les parcours des PR #132 et #164 ne sont pas embarqués. Aucun modèle ni migration
modifié ; les six durées et les traductions existantes sont conservées.


## 9 novembre 2026 — vues publiques explicites (#151)

PR isolée et rebasée directement sur main après fusion de #149.
Privacy, statistics, project et journal disposent chacun d'une vue dédiée.
Le rendu multilingue, les routes, les protections GET/HEAD et le cache sont
inchangés. Les textes de la notice actuellement sur main sont conservés.
Aucun modèle, stockage ou migration ajouté dans ce lot.
## 6 novembre 2026 — correction des six contrôles du bouton employeur

À la demande d’Eric, le test du tableau employeur distingue le libellé
« Importer mon offre d’emploi » de celui de la page publique « Décrire mon besoin
de recrutement », tout en contrôlant leur destination commune. Six combinaisons
FR/EN/DE avec et sans offre, accès au parcours et absence du bouton employeur
pour le conseiller restent vérifiés. Aucun changement de comportement ou de
texte public. Dernière suite complète : 436 tests PostgreSQL réussis, format
Python et diff vérifiés. Travail local uniquement, sans push ni PR.

## Publication Albert au sommet de la pile — 6 novembre 2026

Eric autorise la publication après les essais locaux. La branche est réempilée
sur la PR #144, qui harmonise déjà le bouton partagé et son test ; cette version
est conservée. Les 436 tests précédents concernent le socle local avant cette
actualisation ; la validation sur la nouvelle base est distincte. Aucune fusion
ni activation de production autorisée.

### Validation de publication Albert sur la PR #144

450 tests PostgreSQL réussis après réempilement, migrations sur une base locale
vierge et contrôles Django/migrations, Black, templates, JavaScript et traductions
réussis. La borne de cinq secondes reste dédiée à la regex ; le scénario complet
avec catalogues à froid et Django possède une borne séparée de vingt secondes.
Le texte source et les preuves temporaires sont exclus de l’offre durable même
sans envoi de champs corrigés ; un test couvre ce chemin direct. Les traductions
compilées ont été régénérées après résolution des conflits. La configuration
privée doit encore raccorder le secret pour une recette Albert distante ; aucune
activation d’IA de production ni fusion n’est réalisée.

### Correction CI des tests Albert

Le premier contrôle GitHub de #146 a révélé une dépendance implicite des tests
Albert à l’option locale d’accès au prototype. Les tests déclarent désormais
explicitement `ME_EMPLOYER_DEV_ACCESS=1` et `SHARED_DEMO=False`. Aucune règle
d’accès applicative n’est modifiée. 450 tests PostgreSQL passent aussi sans
options locales implicites ; nouvelle validation GitHub demandée après push.
# 5 novembre 2026 — P1 : confirmation candidat et profil enregistré

Premier lot opt-in local/recette, uniquement données fictives et adresses
`.invalid`, sans email réel. Le questionnaire prépare une demande valable une
heure ; confirmation GET non consommatrice puis POST protégé, compte et profil
créés atomiquement, demande supprimée, session connectée. Consultation et
modification réservées au candidat propriétaire, comptes et profils existants
jamais écrasés. Migrations candidates 0002/0003 additives, dates de vérification
email et lecture déclarée de la notice sans reprise rétroactive.
Simulation email par commande privée et nettoyage des demandes expirées,
comptage sans effacement par défaut. Pas de purge planifiée ni ouverture réelle.
Voir `docs/CANDIDATE_EMAIL_REGISTRATION.md`. Fusion réservée à dejafait.



## 2026-11-06 — ouverture du parcours candidat (#132)

À la demande explicite de dejafait, suppression des restrictions propres à
l’environnement et aux adresses fictives. Le questionnaire, la confirmation
et le profil fonctionnent partout ; les e-mails suivent le backend protégé
commun (production configurée seulement, simulation privée ailleurs).
La recherche publique en lecture seule du catalogue métiers, utilisée par le
questionnaire JavaScript, ne dépend plus non plus du mode démo.
Les vérifications de lien, POST/CSRF et propriété restent en place.
Cette décision remplace le périmètre d’essai limité décrit antérieurement.
Aucun changement de modèle ou migration supplémentaire : la séparation entre
demande temporaire et profil confirmé reste à discuter avant une refonte.

## 9 novembre 2026 — confort du brouillon candidat (PR #132)

À la demande de dejafait, le délai d’inactivité du questionnaire passe de
30 minutes à deux heures. Prolongation, avertissement, notice et textes FR/EN/DE
sont cohérents avec ce délai ; l’avertissement reste deux minutes avant l’échéance.
Les tests couvrent la reprise après une heure d’inactivité et le refus après
plus de deux heures. Aucun changement des modèles ni de la confirmation email.

Les routes privacy, statistics, project et journal ciblent chacune une vue
dédiée. Suppression de l’aiguillage information_page ; rendu multilingue
commun conservé dans _public_page. URL, noms de routes, templates, données
et protections GET/HEAD et absence de cache conservés.
# 6 novembre 2026 — catalogue proposé de 50 métiers

Travail local isolé sur `codex/skills-catalogue-50`, depuis le sommet GitHub
#154 vérifié à `d12374c`. Sept métiers initiaux et leurs sélections conservés,
43 ajouts, même schéma à deux JSON. Données ESCO 1.2.1 FR/EN/DE comparées aux
archives locales épinglées : 50 métiers distincts, 329 compétences distinctes,
615 relations officielles dans le sous-catalogue, 400 propositions de compétences
clés ayant toutes un lien officiel. Sur 200 propositions de savoir-être, 198
associations sont explicitement éditoriales et deux ont un lien officiel.

Chargement des nouveaux intitulés depuis leurs libellés officiels, avec maintien
des intitulés de présentation historiques. Reconstruction en staging identique
octet pour octet. `make skills-pilot-audit` compare les données aux trois archives.
Validation locale : 469 tests PostgreSQL réussis, dont 17 tests du pilote.
Le parcours couvre les 50 métiers, deux rôles et trois langues (300 combinaisons).
Contrôles Django et absence de migration nouvelle vérifiés.
La liste proposée est dans `docs/SKILLS_CATALOGUE_50.md`. Aucun push, fusion,
déploiement ou appel Albert ; aucune nouvelle recette navigateur revendiquée.


## Retrait du parcours autonome — 9 novembre 2026

Après intégration aux formulaires candidat et employeur (#158), les routes
`/skills-pilot/` et leurs écrans sont supprimés. Les catalogues, leurs outils
de maintenance et le service de suggestions restent utilisés par les vrais
parcours. Aucun modèle, migration ou réponse durable n’est supprimé. Les
anciens brouillons de session ne sont plus lus ; aucune purge SQL ajoutée.


## Séparation métiers et compétences — 9 novembre 2026

Les métiers et recherches restent dans occupations ; catalogues de compétences,
suggestions et composant intégré vivent dans [skills](https://github.com/eures-beta/match-europe/tree/codex/extract-skills-app/eures_beta/skills). Le matching est créé séparément par la PR #160. Le transfert du modèle conserve
la table PostgreSQL, les identifiants, les suggestions et les permissions.
## 7 novembre 2026 — secteurs et savoir-être lisibles

Demande d’Eric : voir d’abord les secteurs dans le mode candidat ouvert, puis déplier leurs compétences ; simplifier les savoir-être. Branche `codex/candidate-sectors-readable` sur le sommet #158 `4d171a9` revérifié. Deux listes techniques par secteurs fermés, recherche avec ouverture temporaire et choix conservés ; treize savoir-être avec formulations simples et exemples FR/EN/DE en trois groupes. Identifiants, règles et stockage inchangés, aucune migration. Voir `docs/CANDIDATE_OPEN_SKILLS.md`. La recette distante #158 reste distincte de cette branche tant qu’une nouvelle recette n’est pas ouverte.
# 10 novembre 2026 — lecture des aides aux savoir-être (#159)

Les entrées éditoriales ont des clés lisibles et des champs nommés : groupe,
libellé, description et identifiant ESCO. Identifiants externes, textes gettext,
ordre des groupes et choix enregistrés conservés. Aucun modèle ni migration.
Validation : 506 tests PostgreSQL, Django/migrations, Black et traductions réussis.

## 10 novembre 2026 — noms explicites des modèles de matching (#160)

À la demande de dejafait, deux commits distincts renomment Evaluation en
MatchEvaluation puis Decision en MatchDecision. Deux migrations réversibles
conservent les tables physiques matching_evaluation / matching_decision et leurs
lignes, identifiants et relations ; les ContentType et permissions sont renommés
sans changer leurs identifiants ni les attributions de groupe. Collision de
métadonnées refusée, pas de fusion silencieuse. Aucun calcul ni décision métier
modifié. Les migrations et imports des PR descendantes devront être adaptés à
ces noms lors de leur prochain rafraîchissement ; elles ne sont pas modifiées ici.
Validation : 537 tests après le premier commit, 538 après le second, PostgreSQL,
Django/migrations et Black ; tests aller-retour avec lignes et permissions.
Aucune fusion ni opération sur une base distante.

## 10 novembre 2026 — exigences dans JobOffer (#160)

Sur demande de dejafait, OfferRequirements est remplacé par le champ JSON validé
JobOffer.structured_requirements dans employers. Validation, calcul, seed et
copie d'offre recâblés ; aucun texte libre n'est interprété en critère obligatoire.
La migration copie les valeurs avant de retirer la table redondante ; conflit
refusé sans écrasement. Le rollback restaure les valeurs mais pas les anciens
identifiants/dates techniques des lignes de la table supprimée. Les offres,
leurs dates et les liens de matching sont conservés. 548 tests PostgreSQL, dont
aller-retour de migration, conflits et duplication ; Django/migrations et qualité
Python/HTML/JS/traductions réussis. Pas de fusion ni déploiement par cette tâche.

## 10 novembre 2026 — nom unique du réglage de matching (#160)

Sur demande précise de dejafait, MATCHING_ENABLED devient l'unique nom du réglage
Django et de la variable d'environnement. Ancien alias retiré, valeur par défaut
active et désactivation explicite conservées. Consommateurs, commandes Make et
tests/docs du réglage recâblés. Aucun autre flag, route ou fichier renommé.
Validation : 548 tests PostgreSQL et contrôles Django/migrations, Python, HTML,
JavaScript et traductions réussis. Ni fusion ni déploiement par ce changement.
## 13 novembre 2026 — tous les conseillers ont les mêmes droits métier (#162)

À la demande de dejafait, accès au matching et aux confirmations fondé uniquement
sur la connexion, le compte actif et le rôle conseiller. Les invitations employeur
suivent la même règle, même sans groupe ou permission Django. Les groupes
historiques ne conditionnent plus ce parcours ; les protections de l'administration
Django sont conservées. Pas de migration, de renommage de modèle ni de changement
des réponses ou accords existants.

Tests de régression : deux conseillers sans groupe ni permission peuvent agir ;
les comptes inactifs et les rôles candidat/employeur restent interdits, même si
des permissions matching leur sont attribuées. Les protections de propriété et
CSRF restent couvertes. Suite PostgreSQL locale : 590 tests réussis, sans e-mail
ni service externe réel. Aucun déploiement ou fusion dans ce travail.

## 13 novembre 2026 — quatre noms de modèles explicites dans #162

Choix de dejafait : `CandidateOfferMatch`, `CandidateOfferReview`,
`CandidateOfferReviewAnswer` et `CandidateProfileSharing` remplacent respectivement
`MatchPair`, `ConfirmationRequest`, `ConfirmationAnswer` et `TransmissionAgreement`.
Imports, services, vues, administration, peuplement et tests actuels sont recâblés,
sans alias des anciennes classes. L’accès inverse est `candidate_offer_review`.
Les routes et le contenu métier sont conservés.

La nouvelle migration `matching.0006_candidate_offer_model_names` conserve les
tables physiques, lignes, clés étrangères et identifiants des métadonnées Django.
Elle actualise les noms des types de contenu et permissions administratives,
refuse leurs conflits et permet le retour arrière. Les anciennes migrations
et fixtures historiques gardent leurs anciens noms intentionnellement.

Validation locale : 593 tests PostgreSQL réussis, dont trois nouveaux tests de
registre/admin, données non vides et retour arrière, et refus des métadonnées
incompatibles. Les tests vérifient l’identité physique des tables, les relations,
les dates, les identifiants et la conservation des attributions de permissions.
Django/migrations, Black, HTML, JavaScript et traductions réussis. Aucun e-mail
ou service externe réel. Aucun rebase des descendants, fusion ou déploiement ;
les PR dépendantes devront reprendre ces nouveaux noms lors du rafraîchissement.

## 9 novembre 2026 — socle d’installation PWA candidat

Branche dédiée sur le sommet GitHub #166 (`3585cde`). La pile séparée #132/#169
porte une autre séquence d’inscription. Les vérifications locales utilisent
le parcours présent sur #166.

Le manifeste et l’icône apparaissent sur l’accueil et les écrans du candidat.
Le service worker existant est enregistré et laisse les requêtes au réseau.
Les icônes PNG reprennent le dessin Match Europe déjà présent. La page de
lancement reste l’accueil commun. Le profil validé est récupérable via la
connexion habituelle dans une nouvelle session.

Contrôles locaux : 607 tests PostgreSQL, test ciblé de reconnexion dans une
seconde session, contrôles Django/migrations, Python, HTML et syntaxe JavaScript.
Recette restante sur iPhone et Android : installer, vérifier l’ouverture
du lien de connexion dans le contexte de l’application, récupérer un profil
terminé sur ordinateur puis reprendre un brouillon commencé sur le téléphone.
L’activation du pilote et l’abonnement aux notifications relèvent du lot suivant.

## 10 novembre 2026 — installation proposée après le questionnaire

Sur le profil enregistré, la section « Prochaine étape sur votre téléphone »
ouvre les instructions selon l’appareil. Le candidat peut choisir l’autre
option. Le lien de transfert ouvre un guide public FR/EN/DE et ne contient
aucune donnée du profil. Dans une PWA ouverte sur téléphone, l’écran confirme
le mode application. Les notifications sont annoncées comme une étape à venir.

La section utilise le parcours candidat et le manifeste communs à tous les
environnements. Recette manuelle à faire sur iPhone et Android pour vérifier
l’installation et la connexion au même compte depuis la PWA.

## 13 novembre 2026 — noms techniques de l’installation PWA

Dans la PR176, la vue install_pwa, la route candidate_install_pwa et
/candidate/install-pwa/ remplacent les noms install ambigus. Templates,
partiels, fichier JavaScript, attributs techniques et références sont recâblés.
Textes visibles FR/EN/DE inchangés ; aucun modèle ou migration modifié.
L’ancienne URL propre à la PR n’était pas livrée dans main, donc pas de
redirection de compatibilité ajoutée.

## 12 novembre 2026 — onglet conseiller Inviter

Recette Django locale sur la PR #187 (`8b9a4ce`). Saisie et CSV, aperçu des
modèles génériques français adaptés de Flask, dépôt local, relance et
suppression avant acceptation. Modèle conseiller ajouté, accessible à tous les conseillers actifs pour gérer les
invitations. Le candidat invité peut terminer
son profil après vérification de son adresse par le lien d’invitation.
L’aperçu employeur a été contrôlé dans le navigateur. Voir
[la recette et le contrat](docs/INVITATIONS.md). Le SMTP réel de Brevo
reste à vérifier dans un environnement explicitement autorisé.

## Push candidat universel — correctif de #192

Les notifications utilisent le même parcours en local, recette et production, sans
filtre sur une adresse fictive ni activation des comptes de test. L’absence
d’abonnement navigateur ne bloque pas la validation du rapprochement. La route
canonique est `/candidate/push-subscriptions/`. Authentification, propriété, CSRF,
consentement navigateur et validation des destinations Push sont conservés.
La dérivation de clé et la table existante sont préservées pour les abonnements
déjà enregistrés ; aucune migration supplémentaire. Tests sans notification réelle.
## 13 novembre 2026 — un seul démarrage Django

TRANSVERSE : les huit raccourcis de serveur par parcours sont retirés. Utiliser
`make run PORT=…` avec un port libre par session ; `HOST` reste configurable.
La commande charge le `.env` propre au worktree sans imposer de simulation,
de rôle ou de comptes fictifs. Les anciennes commandes citées dans les notes
datées ci-dessus sont historiques ; voir [le guide actuel](docs/DEVELOPPEMENT.md).
Les évaluations, tests et dispositifs Gunicorn restent distincts. Aucun modèle,
migration, donnée ou parcours métier modifié.


## 13 novembre 2026 — couche web séparée des domaines

À la demande de dejafait, les routes, vues et formulaires d’interface sont rangés
dans `eures_beta/www/` par parcours. Modèles, migrations et services restent dans
les applications métier, qui ne doivent pas importer la couche web. Conserver
les validations partagées dans le domaine. Templates, statiques, traductions et
tests gardent leur rangement commun ; les URL restent inchangées. Aucun modèle
créé ou déplacé, aucune nouvelle migration. Voir
[le guide](docs/ARCHITECTURE_WEB.md).

## 13 novembre 2026 — réglages métier simplifiés

TRANSVERSE : parcours permanents sans interrupteur, autorisation d’e-mail unique
`EMAIL_DELIVERY_ENABLED`, simulation Albert commune `ALBERT_SIMULATED` désactivée
par défaut et contact `EMPLOYER_ADVISER_CONTACT_URL`. Sources, tests et exemples
actualisés ; anciens noms non lus. Aucun modèle ni migration. Les réglages
PostgreSQL et les codes de questions AGLAE restent en discussion, sans modification
de leur comportement dans ce lot. Voir le guide de développement actuel.
