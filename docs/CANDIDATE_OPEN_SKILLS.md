# Candidat ouvert à différents métiers

## Périmètre

Évolution CANDIDATS empilée sur #155, base vérifiée à `692eb517`.
Le questionnaire public conserve quatre étapes. Dans « Mon projet », un mode
explicite permet de poursuivre sans métier avec un écran de trois sections
repliables : savoir-faire, activités à apprendre, savoir-être professionnels.
Le parcours métier et le pilote employeur conservent leurs règles antérieures.
Aucun matching, score, exclusion, envoi supplémentaire ou mise en relation n’est
créé. Les savoir-être ne sont jamais des critères éliminatoires ; leur sélection
exactement par trois est une règle de saisie, pas un filtre d’opportunités.

## Règles et interface

- Savoir-faire : 0–10 ; activités à apprendre : 0–5 ; savoir-être : exactement 3.
- Au moins un savoir-faire ou une activité à apprendre.
- Chaque URI est unique par liste. La même activité ne peut pas être déclarée
  simultanément acquise et à apprendre : demander de corriger ce choix.
- Cases groupées par catégories éditoriales, recherche indépendante dans chaque
  section sur les libellés et synonymes officiels de la langue courante, sans
  distinction d’accents ou de casse. Aucun réseau, IA ou traduction automatique.
- Étiquettes supprimables hors de la partie repliable : les choix restent visibles
  et sélectionnés pendant la recherche. Compteurs annoncés, contrôles natifs au
  clavier, retour du focus après retrait. Les listes commencent repliées pour
  garder les trois sections repérables, même avec 316 activités.
- Sans JavaScript : catégories et cases restent accessibles par les éléments
  `details` natifs ; les étiquettes sont des libellés et le retrait se fait par
  décochage. Recherche et plafonnement immédiat nécessitent JavaScript ; toutes
  les règles de poursuite sont également vérifiées côté serveur.
- Le changement FR/EN/DE du projet est un POST protégé qui conserve même les
  sélections incomplètes. Un projet incomplet reverrouille les étapes suivantes ;
  changer de langue ne permet pas de contourner la validation d’inscription.
- Revenir au mode métier retire les déclarations de compétences lors de la
  validation ; le mode ouvert retire les références et l’intitulé métier.

## Catalogue et provenance

Réutilisation des deux JSON versionnés dans `occupations/data/`, ESCO 1.2.1,
50 métiers et 329 concepts. Aucune copie des traductions ou nouvelle relation
métier–compétence. Les 13 concepts de savoir-être issus des suggestions du pilote
forment une liste éditoriale ; les 316 autres activités forment les choix acquis
et à apprendre. Les listes sont dédupliquées par URI, pas par libellé.
`skill_categories.json` rattache les 50 fiches aux 11 secteurs éditoriaux déjà
utilisés dans la revue du catalogue. Une activité présente dans plusieurs
métiers reçoit le premier secteur rencontré dans l’ordre versionné des fiches.
Ce rattachement n’est ni une hiérarchie ESCO ni une équivalence ROME.
La pertinence sectorielle reste à relire ; ce sous-catalogue n’est pas exhaustif.

Les libellés et synonymes officiels FR/EN/DE restent ceux de #155. La présente
évolution ne réatteste pas une comparaison aux archives officielles ESCO.
Les qualifications et autorisations professionnelles restent à vérifier
séparément ; cocher une activité ne constitue pas une habilitation.

## Stockage, validation et droits

Migration additive `candidates.0005`, après la migration de l’email préalable :
`project_mode`, trois listes JSON dédiées
`acquired_skills`, `learning_activities`, `professional_behaviours`, et
`skill_catalogue_version`. URI ESCO canoniques uniquement ; version fixée par
le serveur à `esco-1.2.1-match-europe-50-v1`, jamais déduite du navigateur.
Les anciens profils restent en mode métier avec trois listes et version vides :
aucune déclaration rétroactive. Le retour arrière retire ces nouveaux champs
et leurs réponses, sans supprimer les profils ni comptes ; aucun retour arrière
sur des données réelles n’est effectué automatiquement.

Après vérification de l’email, le candidat connecté remplit le questionnaire.
Les réponses passent du brouillon privé au profil uniquement après validation
POST explicite. Même validation partagée dans le formulaire, l’enregistrement
et `CandidateProfile.save()`. Aucune table de demande temporaire n’est recréée. La fiche
reste réservée au candidat propriétaire, l’admin n’affiche que les métadonnées.
Aucun partage employeur/conseiller ni nouvelle permission. Pas de coordonnées
supplémentaires collectées, ni de réponses dans les journaux.

Conservation existante : brouillon deux heures après dernière activité, lien
de vérification une heure, profil selon la notice commune (12 mois après dernier contact utile).
Ces échéances ne créent pas de purge physique planifiée. Aucune modification des
transports email, de la confirmation, des durées ou de la notice juridique.

## Vérifier

Dans un environnement local dédié, sans email réel : `make install-test`,
`make install-quality`, `make install-js`, `make db-create`, `make migrate`.
`make candidate-registration-run` expose le questionnaire sur le port local 9035.
Choisir le mode ouvert, ouvrir chaque section, rechercher, cocher, replier,
retirer une étiquette et changer de langue. Essayer un parcours uniquement avec
une activité à apprendre, puis la borne 10/5/3, et les erreurs de saisie.
Continuer jusqu’à la relecture et confirmer uniquement avec une adresse fictive
et la simulation privée existante (`make candidate-email`).

- `make candidate-skills-test` : bornes, identifiants, doublons, modes, langues,
  brouillon incomplet, inscription, revalidation, modèle et droits.
- `make candidate-skills-ui-test` : vrai module JavaScript sur un DOM simulé,
  recherche indépendante, accents, synonymes, sélection masquée, retrait,
  capacité et focus. Ne remplace pas une recette navigateur.
- `make candidate-test` et `make test` : intégration PostgreSQL, migration neuve,
  conservation des anciens profils et retour arrière sur données fictives,
  protections existantes et non-régression employeur/pilote.
- `make check`, `make format-check`, `make format-html-check`,
  `make format-js-check`, `make check-js`, `make translations-check` et
  `make translations-compile` pour les contrôles complémentaires.

Recette navigateur effectuée sur loopback : recherche « cuisine », choix
persistant après recherche sans résultat, changement FR→EN→DE→FR, ouverture au
clavier, sélection de trois savoir-être, fermeture avec étiquettes visibles,
France sélectionnée et passage à l’étape mobilité sans métier. À 390 px, aucun
débordement horizontal du document ou des trois sections. Identité et ressources
EURES existantes préservées. Aucun audit complet WCAG ou test lecteur d’écran
revendiqué, aucune validation sectorielle experte. Aucun déploiement.

## Résultats de cette implémentation

479 tests PostgreSQL réussis, dont 9 scénarios dédiés au projet ouvert et un nouveau scénario de migration ; 3 tests JavaScript dédiés réussis. Installation sur base vide, contrôles Django/migrations, format Python/templates/JavaScript et catalogues FR/DE vérifiés et compilés. Recette navigateur trilingue et mobile effectuée ; aucun audit WCAG complet.
Ces résultats sont locaux ; ils ne prouvent ni fusion ni fonctionnement en production.
