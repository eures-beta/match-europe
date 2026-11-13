# Catalogue métiers local

## Mettre à jour une source avec Django

Trois commandes Django sont exposées par le Makefile :

```bash
make occupations-sync-esco
make occupations-sync-rome
make occupations-sync-esco-rome
```

Elles utilisent les exports complets officiels, sans clé API : archives CSV
ESCO FR/EN/DE, arborescence XLSX France Travail (ROME et OGR ensemble), table
CSV officielle de correspondances ESCO/ROME. Il n’y a pas quatre API distinctes.
Ces téléchargements sont réservés aux opérations de maintenance ; aucun appel
réseau n’est ajouté au fonctionnement de l’application, aux tests ou au démarrage.

La première commande exécutée initialise `.runtime/catalog-staging` depuis
les JSON versionnés, puis rafraîchit uniquement la source demandée. Les suivantes
réutilisent ce staging. Les relations préjointes sont recalculées après chaque
import ; les autres données sources restent conservées. Ne pas exécuter deux
imports simultanément vers le même répertoire.

Par défaut, l’édition du manifeste est retéléchargée ; aucune découverte implicite
de « latest ». Pour une nouvelle version ESCO :

```bash
make occupations-sync-esco CATALOG_VERSION=1.2.1
```

Pour une nouvelle édition ROME, fournir `CATALOG_VERSION` et
`CATALOG_SOURCE_URL` avec l’URL XLSX officielle publiée par France Travail.
L’arborescence doit garder le format attendu (deuxième feuille, colonnes A–E) ;
une évolution de structure demande une revue de l’importateur. La commande
`sync_esco_rome` lit les versions des deux référentiels dans le CSV officiel ;
`CATALOG_SOURCE_URL` permet de choisir une nouvelle publication. Les éditions
de la table de correspondances restent distinctes des éditions courantes des
catalogues : aucune équivalence nouvelle n’est inventée.

`CATALOG_OUTPUT` choisit le répertoire de travail. Les URL personnalisées sont
limitées aux domaines HTTPS officiels ESCO/France Travail ; les redirections
ne sont pas suivies. Délais et tailles de téléchargement/décompression bornés.
Tout téléchargement et parsing doit réussir avant publication des fichiers.
Une disparition d’identifiants bloque l’import : après examen de la source,
`CATALOG_ALLOW_REMOVALS=1` permet de préparer cette suppression pour revue.

Chaque import écrit les quatre JSON, leur manifeste avec empreintes et un
`update-report.json` : identifiants ajoutés, retirés, modifiés et nombre de liens.
Les compétences ne sont pas importées par ces commandes.

Valider le staging :

```bash
make occupations-validate \
  CATALOG_DIR=.runtime/catalog-staging \
  CATALOG_REPORT=.runtime/catalog-staging/validation.json
```

Relire le rapport, puis promouvoir explicitement les quatre JSON et le manifeste
vers `eures_beta/occupations/data/` pour préparer une PR de données :

```bash
make occupations-promote
```

Cette cible refait les contrôles d’intégrité et les recherches multilingues avant
de modifier les fichiers versionnés. Relire ensuite les écarts Git.
Mettre à jour le README d’attribution si les sources changent et relancer les tests.
Les commandes ne créent ni commit ni PR, ne déploient rien et n’écrivent pas en
base de données. Le staging ignoré n’est pas chargé par le site en production.

Les commandes Django sous-jacentes sont `sync_esco`, `sync_rome` et
`sync_esco_rome` ; leurs options sont documentées par leur aide native.

Sources : [ESCO](https://esco.ec.europa.eu/en/use-esco/download),
[ROME](https://www.francetravail.org/opendata/repertoire-operationnel-des-meti.html?type=article).

## Données et limites

Le paquet partagé `eures_beta/occupations/` contient le service et les instantanés
versionnés ESCO/ROME, sans modèle ni migration Django. Il ne dépend d’aucun
parcours candidat ou employeur et ne télécharge rien au démarrage ou à l’usage.

ESCO 1.2.1, pilier métiers complet FR/EN/DE : 3 039 concepts uniques. Les quatre
doublons techniques par langue ne diffèrent que par leur date de modification ;
l’importeur vérifie cette condition avant déduplication. Compétences non importées.
ROME 26M10 : 1 923 fiches, 14 330 appellations. Table française officielle :
13 120 liens, ESCO 1.0.9 / ROME 25M06, publication novembre 2025.

Les sources ont des éditions différentes : 2 046 métiers ESCO ont des codes de
fiches retrouvés ; 22 identifiants d’appellations restent non résolus et quatre
URI de l’ancienne table ne figurent plus dans ESCO 1.2.1. Aucune équivalence
courante Forem/ADEM ni correspondance manquante n’est inventée. Les relations
exactMatch/closeMatch/broadMatch sont conservées. Sources, licences, empreintes et
comptages figurent dans `eures_beta/occupations/data/manifest.json` et son README.

## Recherche

Normalisation des accents/casse, synonymes, priorité à la correspondance exacte,
tolérance aux fautes seulement en l’absence de résultat lexical. Trois propositions
maximum, sans sélection automatique ni modification du texte utilisateur.
Les métiers proches sont ancrés sur le meilleur résultat, suivant les relations
hiérarchiques et le groupe ISCO ; ils ne sont pas des équivalents garantis.
Les instantanés sont vérifiés par SHA-256 avant lecture et mis en cache en mémoire.
Une corruption échoue explicitement, sans repli réseau silencieux.

## Reconstruction hors réseau et mises à jour

Télécharger les archives officielles et la table de correspondances indiquées
au manifeste dans un répertoire local ignoré (par exemple `.runtime/catalog-sources`).
Les noms ESCO attendus sont `esco-1.2.1-fr.zip`, `esco-1.2.1-en.zip`,
`esco-1.2.1-de.zip`. Les sources brutes restent hors Git.

```bash
make occupations-build
make occupations-validate \
  CATALOG_DIR=.runtime/catalog-staging \
  CATALOG_REPORT=.runtime/catalog-staging/validation.json
```

L’importeur est lié aux versions et schémas audités. Il rejette les langues avec
des URI différentes, descriptions absentes, doublons contradictoires et métadonnées
inattendues. Revoir sources, licences, versions, URI retirées et écarts avant de
promouvoir manuellement `esco.json`, `rome.json`, `ogr.json`, `esco_rome.json`,
le manifeste et le rapport validés
vers `eures_beta/occupations/data/`, puis redémarrer pour purger les caches.
Garder les versions précédentes dans Git. Ne pas supprimer ni reclasser des
choix métier existants lors d’un changement de catalogue.

`make occupations-validate` vérifie par défaut le catalogue livré et écrit son
rapport dans `.runtime/`. `make test TESTS=eures_beta.occupations` exécute les tests du catalogue.
`PYTHON`, `CATALOG_SOURCES` et `CATALOG_OUTPUT` sont configurables. Aucun de ces
outils ne télécharge de données ni ne promeut automatiquement un catalogue.

`--previous` accepte un ancien fichier occupations JSON décompressé et compare
URI et libellés ; ce contrôle n’est pas un audit sémantique exhaustif des éditions.
Le rapport livré conserve la trace de l’élargissement historique du pilote de
35 métiers : +3 004 concepts, aucun ancien identifiant/libellé supprimé/modifié.

La veille hebdomadaire locale déjà créée dans Codex reste indépendante de
l’application : alerte sur changement confirmé, aucune mise à jour automatique.
Elle dépend du poste/app et du réseau ; son premier déclenchement n’a pas été
observé. Il n’y a pas de tâche serveur ajoutée par cette PR.

## Validation sur la base du train #74

199 tests PostgreSQL réussis (réseau externe interdit), 31 recherches multilingues
et reconstruction identique des deux catalogues et du manifeste depuis les
sources brutes. Les bases de tests sont distinctes de la recette historique.
