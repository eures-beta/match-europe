# Accueil général — 30 octobre 2026

À la demande d’Eric, le bouton Accueil ouvre une page du prototype reprenant
le contenu de la page publique `/forms/eures-beta/?lang=fr`, consultée dans le
navigateur le 30 octobre 2026. La racine `/` et `/forms/eures-beta/` servent
le même template Django `home.html`, en FR/EN/DE via gettext. Le paramètre
`lang` prime sur la langue du navigateur ; une valeur invalide revient au français.

Contenu repris : introduction, contexte transfrontalier, chiffres clés, parcours
candidat et employeur, principes de l’expérimentation et perspectives. Les chiffres
reprennent la page de référence ; leur source statistique n’a pas été vérifiée.
Les versions anglaise et allemande sont des traductions de ce contenu français.

Présentation et logos officiels repris des pages existantes du prototype.
L’accueil est une page de présentation accessible hors démo ; il n’ouvre aucun
accès métier supplémentaire et ne crée aucun profil, import ou compte.
Les liens candidat et employeur mènent aux pages locales existantes et conservent
la langue. Les protections de ces parcours restent inchangées. Les autres liens
du menu (statistiques, projet, journal) sont conservés : ces pages ne sont pas
implémentées par ce lot.

Tests ciblés : contenu et liens dans les trois langues, priorité de la langue,
compatibilité des deux adresses, retour depuis les deux parcours, refus des
écritures et navigation linguistique existante. Pas de modèle ni migration.
Eric a ensuite autorisé le push et une nouvelle PR au-dessus de la pile,
intitulée « Mise en place page d'accueil ». Aucune fusion ni mise en production.
