# Landing employeur — proposition locale

Prévisualisation FR/EN/DE du parcours fondé sur le dépôt d'une offre existante. Réutilise le gabarit et le CSS de la landing historique ; aucune route applicative ni donnée métier n'est modifiée.

Depuis la racine du dépôt :

```sh
node previews/employer-landing/build.cjs
python3 -m http.server 8015 --bind 127.0.0.1
```

Ouvrir `http://127.0.0.1:8015/previews/employer-landing/fr.html`.

Les trois HTML sont générés depuis `copy.json` et le gabarit existant. Le bouton ouvre désormais la prévisualisation interactive d’import (`import-fr.html`, EN/DE disponibles). Choix et remplacement du PDF (10 Mo maximum, vérification de l’en-tête), saisie manuelle, puis email. Ces valeurs restent uniquement en mémoire dans la page ; aucun envoi ou stockage. La lecture et l’analyse serveur restent à raccorder. Un écran explicite cette limite après l’email. Les autres liens utilisent les chemins historiques locaux et ne constituent pas un parcours fonctionnel complet sur le serveur statique.

Le contenu présente le parcours cible, pas les capacités déjà disponibles en production. Logos, couleurs et mise en page existants sont conservés ; aucune nouvelle conformité graphique ou certification WCAG n'est revendiquée. Les logos externes gardent leurs adresses d'origine.

Aucun push, aucune PR ni aucun déploiement ne fait partie de cette étape.

## Pages juridiques retrouvées

Seule la notice Protection des données existe localement (`forms/eures-beta/privacy.html`, contenu FR/EN/DE dans `app.js`). Elle est reprise avec une section locale sur la préqualification (`privacy-prequalification.json`) dans `privacy-fr.html`, `privacy-en.html`, `privacy-de.html` pour que le lien fonctionne sur le serveur statique. Un avertissement indique sa date et son inadéquation au nouveau parcours. CGU, mentions légales, déclaration d'accessibilité et page de gestion des cookies non trouvées dans le code local : aucun lien fictif ajouté.

## Logos de la landing

Les quatre fichiers proviennent de `eures-beta-logos-pr/assets/partners` : EURES/ELA, bloc marque République française/France Travail, ADEM et Forem. Copies intégrales sans retouche ni recadrage. Ils sont servis localement, sans appel externe. Voir le README de ce dossier source pour leur provenance et les consignes de marque. La signature nominative du dossier LOGOS/FOREM reste inchangée et n'est pas publiée. Le 21 octobre 2026, `assets/forem.png` a été remplacé par une copie exacte de « Forem_LOGO new (4).png », officiellement transmis à Eric et fourni pour ce remplacement, sans retouche ni recadrage (795 × 229 pixels).

Validation import : scénario navigateur PDF fictif → email fictif → limite de simulation, retour à zéro et absence de fichier vérifiés. JavaScript vérifié avec node --check. Contrôles des liens et génération FR/EN/DE effectués. Aucun changement au backend ou à PostgreSQL.

Option lien d'offre : écran URL FR/EN/DE, validation syntaxique HTTPS sans identifiants, refus des IP et adresses locales évidentes, puis email et accord. Aucun fetch ni résolution DNS : la validation navigateur ne prouve pas que la page est publique. Avant tout raccordement, contrôler DNS, IP résolues et chaque redirection côté serveur, taille, délais, types de contenu et protections contre les requêtes vers le réseau interne. Test navigateur : adresse locale refusée, lien HTTPS fictif accepté, retour conservant le lien. Aucun appel AGLAE.

## Vérification de l’offre

Après l’email et l’accord, la fiche de vérification est accessible en FR/EN/DE. Pour l’URL Moovijob testée, elle reprend une copie datée du retour réel AGLAE (`aglae-offer-snapshot.json`), sans appel réseau. La localisation approximative est signalée. Aucun contact ni secret dans cette copie. Pour les autres liens/PDF, fiche vide explicitement signalée ; pour la saisie manuelle, texte repris dans la description. Les questions proposées sont propres à cet exemple et ne sont jamais utilisées pour une autre source.

Champs modifiables, demandes d’éclaircissement préparées par Match Europe, frontaliers/déménagement, questions sélectionnables et modifiables, caractère indispensable soumis à revue humaine. Les informations manquantes restent ouvertes. Brouillon sauvegardé par téléchargement JSON volontaire, hors serveur et sans email ni accord de préparation. Validation locale nécessitant champs essentiels et confirmation ; toute modification révoque cette confirmation et le téléchargement de la fiche validée. Aucun envoi AGLAE, matching ou SMS depuis l’écran. L’export n’est pas un payload API prêt à transmettre : mapping, géocodage précis, contrôles serveur, authentification et sauvegarde réelle restent à raccorder.

Validation écran de vérification : scénario Moovijob → email/accord → fiche réelle ; validation bloquée sans confirmation ; validation locale réussie ; changement annulant confirmation ; autre URL ne réutilisant ni les données ni les questions de l’offre testée ; téléchargement JSON relu, sans email/consentement, inactive et sans questions présélectionnées. Capture contrôlée sans débordement à la largeur du navigateur.

## IMPORTANT — Raccordement réel

Les sections précédentes décrivent les étapes historiques de maquette. Sur le serveur Django local 8015 avec `ME_EMPLOYER_LOCAL_API=1`, la lecture de chaque source, les brouillons PostgreSQL et l’envoi/relecture AGLAE après validation sont désormais réels. Voir `../../eures_beta/README.md` pour lancement, routes, limites et tests. Le serveur Python statique ne fournit pas ce fonctionnement.

### Conditions du poste et préqualification

Le point 2 recueille les conditions de travail, permis requis et aides à l’arrivée (FR/EN/DE). Les réponses structurées sont validées et conservées dans le JSON du brouillon PostgreSQL, puis jointes au contexte de l’offre inactive lors de sa validation. Les cases « aucune » et « à préciser » sont exclusives des autres choix. Les permis masqués après un « non » ne sont pas enregistrés. Un bouton propose des questions adaptées sans les activer ni écraser les textes personnalisés. Le bloc de protection des données distingue le futur usage EURES du test local sans transmission aux partenaires.

Après validation confirmée par le serveur, la vue de confirmation remplace le formulaire et présente un récapitulatif replié en lecture seule. Reprendre une offre déjà synchronisée ouvre cette confirmation. Un échec conserve le formulaire et ses corrections.

La consultation OpenStreetMap est facultative : encart sous le lieu exact, sans case de confirmation. La localisation automatique est recalculée côté serveur lors de la validation si le lieu a changé.

### Rétablissement demandé le 15 octobre
Textes et styles des écrans lien/email/vérification rétablis à l’état précédant les dernières retouches UX. Conservés : encart OSM sous le lieu, consultation facultative et lien unique, confirmation après succès, partie 3 masquée, blocage des pages de résultats. La version précédente reste conservée dans le checkout local d’origine, hors de cette publication.
