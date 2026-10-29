Note de reprise : une seule configuration Django existe désormais à la racine.
Utiliser le Makefile et le README principal ; les anciens lanceurs autonomes
mentionnés dans les notes historiques ci-dessous ont été supprimés.

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
