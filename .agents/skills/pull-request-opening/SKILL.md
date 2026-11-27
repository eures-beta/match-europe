---
name: pull-request-opening
description: Ouvrir une pull request Match Europe avec le dernier template partagé, ses aperçus visuels et une base vérifiée dans la pile active. Ne concerne pas la fusion ou le déploiement.
---

# Ouvrir une pull request

Lire AGENTS.md et [le guide commun](../../../docs/AGENT_WORKFLOW.md).
Une ouverture ne donne aucune autorisation de fusion ou déploiement.

## Préparer la description

À chaque ouverture, récupérer sur GitHub la version actuelle de
`eures-beta/.github`, branche `main`, fichier `pull_request_template.md`.
Ne pas réutiliser une copie locale, une ancienne description ou un template
chargé au début d'une longue tâche sans en vérifier les changements juste avant
publication. Si le template est inaccessible, signaler cette limite.

Remplir en français toutes les sections pertinentes, remplacer les aides,
décrire données/modèles/migrations, tests effectivement exécutés et limites.
Respecter les instructions visuelles du template actuel : avant/après avec
données et cadrage comparables, légendes claires, six images maximum au total.
Utiliser des données fictives et préciser aperçu local ou application réelle.
Inspecter les images avant publication : aucune capture blanche ou trompeuse.
Joindre les images dans GitHub (éditeur ou CLI officielle avec pièces jointes),
jamais dans un commit ou une branche d'hébergement. Vérifier ensuite leur rendu
et leur accessibilité aux relecteurs. « Sans objet » seulement si une capture
n'apporte aucune information utile ; annoncer une limite réelle au lieu d'inventer.

## Choisir la base au dernier moment

Par défaut, les PR actives forment une unique pile linéaire : ouvrir au-dessus
de sa tête actuelle, pas à côté. Les exceptions explicites (urgence directement
sur main, travail indépendant, brouillon isolé) sont conservées et expliquées.
Ne pas déduire l'ordre des numéros de PR ou de leur date : examiner bases,
branches et SHA des PR ouvertes, puis leur ascendance Git réelle.

Immédiatement avant la création, relire les PR ouvertes et la tête distante de
la pile. Si la tête a changé pendant le travail, adapter sa propre branche et
valider son diff et les contrôles nécessaires avant d'ouvrir. Ne pas réécrire
une branche concurrente ni modifier une PR indépendante sans autorisation.

## Vérifier après ouverture

Relire la liste des PR, leurs bases et SHA : une création concurrente peut
avoir produit deux enfants du même parent malgré le contrôle précédent.
Vérifier que sa PR est dans l'unique chaîne attendue, avec seulement son diff
propre, et que description et images publiées correspondent au SHA final.
En cas de fork, corriger sa propre PR par rebase/retarget avec vérifications et
lease explicite si nécessaire ; préserver le travail et les auteurs concurrents.
Ne jamais pousser une tête qui deviendrait ancêtre de la base d'une PR ouverte :
sécuriser d'abord les bases concernées selon la maintenance de pile. Si la
correction exige de changer le travail d'autrui, coordonner ou signaler le blocage.
Ces deux lectures réduisent les courses ; elles ne constituent pas un verrou GitHub.

Assigner au demandeur identifié, demander la relecture selon AGENTS.md et
signaler les refus. Fournir le lien et les vérifications, sans fusionner.
