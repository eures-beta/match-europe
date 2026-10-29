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
