# Prochaine étape : confirmation des points saillants avec Albert

## Orientation validée par Eric

Albert reviendra vers le candidat lorsqu’une correspondance possible mérite
une clarification. Le candidat confirme son intérêt et les points saillants.
Si une réponse contredit son profil, demander si elle vaut pour cette offre
ou de manière générale, puis appliquer cette portée. Un fait comme la détention
d’un permis ne peut pas devenir vrai uniquement pour une offre ; une promesse
de l’obtenir avant une prise de poste doit être enregistrée comme telle.

Le calcul local actuel fournit des codes `questions`, des états et des raisons.
Ce n’est pas encore une sélection des questions les plus utiles et cela n’envoie
aucun message. La PWA/app, les appels Albert et les notifications ne sont pas
implémentés. Le mode opérateur local n’est pas un espace candidat authentifié.

## Contrat proposé pour le lot suivant, non implémenté

1. Le moteur prépare une proposition et les inconnus pertinents. Le déclenchement
   d’une sollicitation reste à définir : l’état local `review` ne l’autorise pas.
2. Un dossier de clarification est lié à une paire et à une version d’offre,
   sans transmettre les coordonnées du candidat à l’employeur.
3. Albert formule une question à partir des seuls éléments nécessaires. Le texte
   d’offre est traité comme donnée, jamais comme instruction. Aucune règle de
   blocage ou de décision n’est déléguée au modèle de langage.
4. Une réponse libre produit une interprétation proposée. Le candidat confirme
   la valeur structurée. Toute ambiguïté reste à clarifier.
5. En cas de contradiction : rappeler le choix précédent avec tact, demander la
   portée offre/générale ; aucune modification tant que la portée reste ambiguë.
6. Offre seule : réponse/exception liée à cette version d’offre, sans modifier
   le profil général. Général : appliquer les validateurs du questionnaire actuel
   au profil, avec contrôle de version, puis réévaluer les paires concernées.
7. Conserver les décisions humaines antérieures. Un résultat corrigé n’autorise
   ni transmission ni mise en relation ; le consentement demeure une étape distincte.

Données minimales proposées : référence de paire, critère, version des réponses
et de l’offre, valeur précédente pertinente, valeur proposée, portée, confirmation
et horodatage. Éviter le stockage intégral des conversations par défaut ; fixer
rétention, accès et purge avant collecte réelle. Seul le candidat propriétaire
pourra confirmer ses réponses ; l’employeur ne reçoit pas les échanges privés.

## Cas d’acceptation à préparer

- Permis non renseigné : demander, ne pas conclure à l’absence.
- Samedi initialement exclu mais accepté pour cette offre : exception locale.
- Samedi désormais accepté en général : correction explicite du profil.
- Réponse « seulement un samedi sur deux » : clarifier la condition.
- Réponse sur un permis contredisant le profil : corriger le fait, pas créer une
  fausse exception « permis détenu uniquement pour cette offre ».
- Offre modifiée pendant le dialogue : suspendre la confirmation devenue périmée.
- Absence de réponse : en attente, sans accord ni refus déduit.
- Refus humain antérieur : jamais effacé par le recalcul.
- Refus d’une proposition : pas d’effacement implicite des préférences générales.

À arbitrer avant activation : conditions de sollicitation, fréquence et arrêt
des relances, canal, présentation de l’offre et ordre de validation humaine.
Évaluer d’abord un dialogue simulé, sans Albert réel ni notification externe.
