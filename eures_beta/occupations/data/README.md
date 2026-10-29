# Catalogues métiers embarqués — 29 octobre 2026

- `occupations.json.gz` : **3 039 métiers ESCO 1.2.1**, FR/EN/DE, intitulés,
  synonymes, descriptions, groupes ISCO et relations hiérarchiques du pilier métiers.
  Les compétences du pilier ESCO skills ne sont pas importées dans l’application.
- `rome.json.gz` : **1 923 fiches et 14 330 appellations ROME 26M10**, ainsi que
  les **13 120 lignes** de la table officielle ESCO/ROME France publiée en 2025.
- `manifest.json` : schéma, versions, URLs, empreintes SHA-256, décomptes,
  traitements et attribution. Les archives sources originales sont conservées
  localement hors Git (répertoire de travail indiqué dans la procédure).
- `validation.json` : contrôles de couverture et 31 recherches multilingues,
  avec comparaison au précédent échantillon. Mesures locales, sans garantie SLA.

Le runtime charge ces fichiers sans réseau avec vérification des empreintes.
Aucune migration, téléchargement au démarrage ou nouvelle dépendance applicative.

## Provenance et attribution

**ESCO : © Union européenne / Commission européenne**, version 1.2.1.
Sources : archives CSV FR, EN, DE liées depuis
https://esco.ec.europa.eu/en/use-esco/download . URLs exactes et SHA-256 dans le
manifeste. Réutilisation et attribution :
https://commission.europa.eu/legal-notice_en (CC BY 4.0 sauf indication contraire).
Traitements effectués : fusion des langues par URI, conservation des textes,
déduplication de quatre URI par langue dont seule la date de modification diffère,
extraction des seules données métiers utiles au produit, regroupement des liens.
Les 3 043 lignes par langue représentent 3 039 concepts uniques.

**ROME : France Travail**, arborescence principale d’octobre 2026 (26M10),
https://www.francetravail.org/opendata/repertoire-operationnel-des-meti.html?type=article .
Conditions de réutilisation publiées par le producteur :
https://www.francetravail.org/files/live/sites/peorg/files/documents/Statistiques-et-analyses/Open-data/ROME/rome_licence_ouverte.pdf .
Extraction de l’arborescence et jointure exacte sur identifiant Code OGR ; pas de
conversion d’une ressemblance de mots en équivalence de métiers.

**Correspondances : France Travail / Commission européenne**, projet V1.1 du
19 novembre 2025, ESCO 1.0.9 / appellations ROME 25M06, fichier officiel :
https://esco.ec.europa.eu/system/files/2025-12/EURESmapping_occs_FR.csv .
Les relations SKOS et toutes les lignes sont conservées dans `rome.json.gz`, y
compris quatre URI absentes du catalogue ESCO courant. Aucun lien Forem ou ADEM
courant n’est déduit de ce fichier français.

## Limites des correspondances

2 047 métiers ESCO ont une entrée dans la table ; 2 046 ont au moins une fiche
ROME retrouvée dans l’arborescence. 22 identifiants d’appellations de la table
historique n’existent pas dans l’arborescence 26M10 ; liste dans le manifeste.
L’absence d’un lien ne signifie ni absence d’un métier ni absence d’équivalence
possible. La jointure d’identifiants entre éditions ne certifie pas la stabilité
des définitions ; les deux versions sont exposées dans l’interface.

Les groupes/relations servent à proposer des descriptions proches, jamais à
attribuer des compétences ou à décider d’une adéquation candidat/offre.

## Reconstruction et mise à jour

Voir `docs/OCCUPATION_CATALOG_MAINTENANCE.md`. Les scripts n’effectuent pas de
publication : construire en staging, valider, comparer et remplacer explicitement
les fichiers embarqués. Les gzip sont déterministes (mtime=0) ; deux constructions
sur les mêmes sources ont produit des fichiers et manifestes identiques.
Le rapport conserve la comparaison historique avec les 35 métiers du pilote.
Cet échantillon expérimental n’est pas réintroduit dans le train.
