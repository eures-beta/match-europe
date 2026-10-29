# Catalogue métiers local

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

```sh
rtk proxy python3 scripts/esco/build-catalog.py \
  --esco-dir .runtime/catalog-sources \
  --mapping .runtime/catalog-sources/esco-rome-other.csv \
  --rome .runtime/catalog-sources/rome-oct2026.xlsx \
  --output .runtime/catalog-staging
rtk proxy python3 scripts/esco/validate-catalog.py \
  .runtime/catalog-staging --report .runtime/catalog-staging/validation.json
```

L’importeur est lié aux versions et schémas audités. Il rejette les langues avec
des URI différentes, descriptions absentes, doublons contradictoires et métadonnées
inattendues. Revoir sources, licences, versions, URI retirées et écarts avant de
promouvoir manuellement les deux `.json.gz`, le manifeste et le rapport validés
vers `eures_beta/occupations/data/`, puis redémarrer pour purger les caches.
Garder les versions précédentes dans Git. Ne pas supprimer ni reclasser des
choix métier existants lors d’un changement de catalogue.

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
