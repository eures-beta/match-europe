---
name: stack-maintenance
description: Vérifier, rafraîchir ou préparer la fusion explicitement autorisée d'une pile de PR Match Europe, en préservant les commits et les validations de chaque étage.
---

# Maintenance de pile

Lire la [procédure commune](../../../docs/AGENT_WORKFLOW.md) et les consignes
actuelles ; cette procédure ne donne aucune autorisation de fusion ou déploiement.

Relever PR ouvertes/fusionnées, bases, SHA et appartenance aux piles. Identifier
les travaux concurrents avant mutation. Une pile active contient seulement les PR
destinées à la production encore ouvertes, dans leur ordre de dépendance ;
exclure les essais/backups et les PR explicitement indépendantes.

Sur demande de rafraîchissement, actualiser les références et les commits propres
de chaque PR. Rebaser sur le bon parent, sans merge ni squash ; préserver auteurs,
commits concurrents et brouillons. Utiliser une lease explicite pour une réécriture,
après vérification de la tête distante. Ne pas écraser un nouveau commit inattendu.

Après conflit, revoir le comportement de la PR et réappliquer les qualités héritées.
Valider chaque étage modifié : tests PostgreSQL, Django/migrations, Black, HTML/CSS,
JavaScript et gettext ; utiliser les cibles communes sans wrapper ni longue recette.
Isoler une remise en conformité dans un commit supplémentaire quand cela clarifie la revue.

Contrôler le diff propre de chaque PR contre sa base et les CI du SHA final.
Un job ignoré/annulé n'est pas un succès de test ; consulter les vrais jobs exécutés.
Après #209, vérifier le push réel pour une branche interne.

Fusion uniquement sur demande explicite, après destination à jour et validations.
Respecter les protections GitHub, sans bypass ; vérifier ensuite le commit réellement
servi si une livraison est autorisée. Retargeter les descendantes directes,
supprimer une branche seulement quand elle ne sert plus, puis maintenir une pile
active sans PR fusionnées. Pas de rebase spontané des PR indépendantes.

Dans le retour, distinguer ce qui a été rebasé, testé, publié, fusionné et déployé.
Liens des PR et preuves actuelles ; ne pas présenter une intention comme un résultat.
