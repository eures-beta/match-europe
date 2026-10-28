# Lecture d’une offre par URL

La lecture prépare un résumé à vérifier par l’employeur ; elle ne publie pas
l’offre et ne déclenche pas de recherche de candidats.

## Adaptateurs ciblés

- **EURES** : seules les URL `https://europa.eu/eures/portal/jv-se/jv-details/<identifiant>`
  sont reconnues. Le site charge l’offre avec JavaScript ; son HTML initial ne
  contient que « Loading… ». L’adaptateur lit la ressource JSON publique utilisée
  par ce site, sous `/eures/api/jv-searchengine/public/jv/id/`, et vérifie l’identifiant
  retourné. Il refuse les redirections de cette ressource et les réponses invalides,
  sans se rabattre sur le texte de la page d’accueil.
- **France Travail** (traitement existant, inchangé) : une URL individuelle
  `/offres/recherche/detail/<identifiant>` est convertie en lecture de la ressource
  publique `/api-descriptifoffre/offre/<identifiant>`. Le numéro d’offre reçu est
  vérifié. L’adresse de l’agence ne remplace pas le lieu de travail. Ce traitement
  n’utilise pas l’API partenaire authentifiée de France Travail.
- Les autres sites passent par le lecteur HTML/JSON-LD générique. Celui-ci
  n’exécute pas JavaScript ; certains sites restent donc incompatibles.

## Périmètre EURES

Importer le titre, l’employeur, les lieux de travail et la description, y compris
le texte des avantages/rémunérations. Préférer la version indiquée par
`jvDisplayLanguage` lorsqu’elle existe, sinon la langue préférée de l’offre,
puis une version disponible. Aucune traduction automatique n’est demandée.
Les autres champs restent à compléter : « fulltime » ou « directhire » ne
permettent pas de déduire un CDI. Les contacts et liens de candidature ne sont
ni suivis ni utilisés comme coordonnées de l’employeur dans notre parcours.

## Protections et limites

Pas de navigateur, de cookie de connexion, de jeton, de dépendance supplémentaire
ou d’exécution du contenu externe. Le lecteur partagé conserve HTTPS, validation
des adresses publiques et connexion TLS à l’adresse DNS vérifiée, limites de
durée/type/taille (2 Mio). Les textes externes sont traités comme des données.

Les ressources JSON utilisées par les sites ne constituent pas une garantie
d’API stable : une évolution de leur schéma peut nécessiter une adaptation.
Les tests automatisés utilisent des données fictives et des réponses simulées,
sans appels réseau. `make test` couvre la lecture, les refus et la préparation du
résumé avec consentement, avant toute sauvegarde d’offre.
