# Choix du métier dans la fiche employeur

## Périmètre

Reprise de l’essai local sur l’architecture du train : `employers` pour les imports
et `occupations` pour les références communes. Le template unique
`templates/employer/import.html` utilise un fragment gettext FR/EN/DE pour le
widget ; aucun générateur, copie HTML par langue ou code candidat réintroduit.

Après lecture d’un document/lien, l’intitulé existant déclenche les propositions.
Après saisie manuelle, renseigner l’intitulé puis « Trouver des descriptions ».
Le lecteur manuel conserve le texte de l’offre sans en déduire son intitulé.
Les propositions ne sont jamais cochées automatiquement ; plusieurs choix sont
possibles, sans remplacer les missions de l’offre ni l’intitulé saisi. Si rien ne
convient : métiers proches, puis description personnelle sans code inventé.
Changer le titre efface les choix et la description personnelle de l’ancien titre.
Les références ESCO/ROME, relations et éditions sont repliées dans chaque carte.

Les brouillons peuvent rester incomplets. La validation d’une fiche comportant
le nouveau bloc exige une description sélectionnée ou personnelle ; les anciens
brouillons sans bloc restent compatibles. Le mode de recette locale conserve son
blocage des services externes : enregistrement local testable, validation distante
non activée. Aucun nouveau contrat AGLAE, matching ou contact candidat.

## Contrat

`GET /api/occupations/?q=…&lang=fr&mode=search` : version et au plus trois
propositions locales. `mode=near` accepte des `excluded` répétés. Le garde commun
`require_demo_access` conserve les conditions démo/HTTPS partagé ou loopback
explicitement activé ; tailles, langues, modes et URI sont contrôlés côté serveur.
Aucune nouvelle permission, aucun réseau ESCO à l’usage.

Le JSON `EmployerImport.data.occupation` contient `title`, `language`, `version`,
`uris`, `personal`, `jobs`. Le serveur reconstruit descriptions, codes et relations
depuis le catalogue ; les libellés/codes du navigateur ne font pas autorité.
L’objet suit les droits existants session/établissement et le contrôle de révision.
La réouverture du même import restaure les cases et le texte personnel. Aucun
changement de modèle ni migration. Le bloc n’est pas envoyé au prestataire.
L’éditeur connecté historique conserve les choix tant que le titre ne change pas,
mais n’intègre pas encore le widget ; modifier le titre retire ce bloc.

## Validation du 29 octobre 2026

202 tests Django/PostgreSQL passent avec réseau externe interdit, dont les
migrations aller-retour de la base du train. Contrôles de propriété du brouillon,
révision, URI forgée, version, titre incohérent, minimum avant validation,
reconstruction des données serveur et JSON gettext FR/EN/DE.
Black, djLint, vérification/compilation des traductions et contrôles Django passent ;
aucune migration oubliée. Recette navigateur sur base distincte : offre fictive
boulanger, deux descriptions choisies, enregistrement et réouverture avec cases
cochées ; changement de titre effaçant les anciens choix vérifié sans sauvegarde.
La recette historique et le travail candidat restent préservés séparément.

## Correction des intitulés enrichis

Les mentions de recrutement comme `(m/f/x)`, `(H/F)`, le contrat et les horaires
placés en suffixe sont ignorées pour la recherche, sans modifier le titre conservé.
Pour un titre générique sans correspondance exacte, le service cherche aussi des
libellés/synonymes ESCO explicites de trois mots au moins dans les missions et le
profil, dans les trois langues. Un intitulé exact reste prioritaire. Ce mécanisme
n’est pas une compréhension sémantique générale ; les propositions restent à
confirmer, sans attribuer automatiquement de métier ou de compétence.

Le widget utilise désormais `POST /api/occupations/` (JSON, CSRF) avec `q`, `lang`,
`mode`, `excluded`, `context` : le contexte, limité à 20 000 caractères, ne figure
pas dans l’URL et n’est pas enregistré par cet endpoint. Le GET reste compatible
pour les recherches simples. Aucun envoi à un service tiers.
203 tests PostgreSQL réussis ; régression titre enrichi/contexte multilingue,
priorité au titre exact, limites et CSRF. Import d’un PDF fourni puis recherche
automatique et au clic vérifiés dans le navigateur local. Le fichier n’est pas
ajouté au dépôt ni aux fixtures.

## Essai local : recherche indépendante et saisie progressive

Branche `codex/occupation-picker-live-trial`, hors train publié en attente de
validation ergonomique. Champ métier distinct du titre de l’offre : prérempli
à l’ouverture, propositions après deux caractères et 300 ms de pause, requêtes
précédentes annulées ; saisie/Entrée et bouton restent utilisables au clavier.
Les choix déjà retenus sont conservés et présentés séparément des propositions.
Le titre n’est pas remplacé par une suggestion ou par le texte de recherche.

Une section repliée permet une référence exacte : code de fiche ROME à cinq
caractères, code métier ESCO, UUID ou URI ESCO complète. Le mode API `reference`
retourne les liens du catalogue versionné, au plus 20 résultats avec total et
indication de limite ; aucune équivalence unique supposée pour un code ROME.
La saisie explicite n’est pas surclassée par le contexte du document.
La description personnelle et la sélection multiple restent possibles.

204 tests PostgreSQL réussis hors réseau externe, puis 38 tests catalogue/import
repassés après finalisation des textes. Contrôles gettext et HTML réussis. Recette
navigateur : recherche bibliothécaire indépendante du titre boulanger, choix
conservés, propositions automatiques sur « boul » et recherche ROME D1102 vérifiés.
Aucune publication de cet essai, aucune nouvelle migration ni intégration candidat.

### Révision de l’essai : recherche manuelle seulement en recours

À la demande d’Eric, l’intitulé extrait n’est plus recopié dans un deuxième champ
visible. À l’ouverture : recherche depuis le titre et affichage direct des
correspondances. Si aucune n’est trouvée : message explicite et champ manuel vide,
avec recherche progressive et alternative ESCO/ROME. Si les propositions ne
conviennent pas, le bouton correspondant ouvre le même recours manuel.
Un changement de titre relance automatiquement la recherche après une courte
pause. La description personnelle n’apparaît qu’après un essai manuel infructueux.
Aucun changement d’API ou de modèle ; essai toujours local, hors train publié.
Cas avec/sans résultats vérifiés au navigateur ; traductions FR/EN/DE compilées
et vérifiées, syntaxe JS et HTML contrôlés.

### Recherche unifiée dans le recours manuel

Le même champ accepte désormais intitulé, code ROME à cinq caractères ou
référence ESCO (code métier, UUID, URI). L’API reconnaît automatiquement ces
formats dans le mode search ; le mode reference explicite reste compatible.
L’option de saisie de code séparée est retirée de l’interface. Détection et droits
couverts par les 38 tests ciblés ; l’auto-complétion et le titre indépendant
restent conservés. Essai local en attente de validation UX.

### Présentation épurée du recours

Le bouton de recherche est retiré : saisie progressive et touche Entrée suffisent.
Titre et paragraphes répétitifs supprimés, label court Rechercher un métier et aide
Intitulé ou code ROME/ESCO. Le message spécifique d’échec automatique demeure au
premier affichage concerné. Les annonces de progression/résultat restent
accessibles aux lecteurs d’écran ; les cartes gardent leurs descriptions et références.

## Livraison de la recherche améliorée

Les sections d’essai ci-dessus décrivent les étapes historiques. Eric autorise
leur publication au sommet du train, après la PR #77, sous le titre
« amélioration de la recherche de métiers ». Le comportement final est le suivant :
recherche automatique depuis l’intitulé conservé ; propositions à confirmer ;
champ manuel vide immédiatement visible si aucune correspondance automatique ;
sinon bouton de recours après les cartes. Le même champ accepte texte, ROME ou
ESCO, avec recherche pendant la saisie et touche Entrée, sans bouton de recherche.
Les choix retenus restent conservés entre recherches ; aide et focus sont espacés.
38 tests PostgreSQL catalogue/imports repassés avant publication, sans réseau
externe ; Black, syntaxe JavaScript et format des deux templates contrôlés.
Aucune migration, aucun changement candidat, aucune fusion ni déploiement.

## Essai du 30 octobre — recherches indépendantes ESCO et ROME

Sur demande d’Eric, une saisie alimente deux recherches locales distinctes.
ESCO garde ses descriptions multilingues ; ROME recherche directement les
appellations françaises et codes des fiches 26M10, sans utiliser la table de
correspondance. Les descriptions détaillées ROME ne sont pas disponibles dans
cet instantané et ne sont pas inventées. Trois fiches maximum sont proposées,
regroupées par code, avec quelques appellations ayant effectivement répondu
à la recherche. Les résultats proches restent à confirmer ; aucun choix automatique.

Le champ JSON `occupation` conserve séparément `uris`/`jobs` pour ESCO et
`rome_codes`/`rome_jobs`/`rome_version` pour ROME. Le serveur contrôle les codes
et reconstruit les intitulés depuis le catalogue. Les anciens brouillons restent
compatibles. Au moins un choix dans l’un des référentiels ou une description
personnelle est nécessaire ; aucun choix double imposé. Pas de conversion
ESCO–ROME automatique, migration, appel externe ni effet sur le rapprochement.
La liste de correspondances ROME est retirée des cartes ESCO de cet essai.
