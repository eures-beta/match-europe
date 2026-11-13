# Parcours candidat

## Version actuelle : projet guidé sans CV

À la demande d’Eric, le questionnaire historique Flask sert d’inspiration fonctionnelle, avec recherche ESCO/ROME conservée. L’import CV, les expériences professionnelles, formations, diplômes, compétences et leurs propositions d’extraction sont retirés de ce parcours. Cette décision remplace la proposition locale initiale à cinq étapes. Le lecteur employeur reste inchangé. L’ancien scénario fictif supprimé de main n’est pas réintroduit.

### Essayer

`make run PORT=9031` démarre http://127.0.0.1:9031/candidate/?lang=fr. Un seul bouton ouvre le questionnaire, sans étape d’import. Utiliser des données fictives. `make test TESTS=tests.candidates` teste le domaine candidat ; `make test` vérifie les interactions du socle.

### Quatre étapes

1. **Projet** : recherche ESCO FR/EN/DE et ROME direct en français, sélections multiples indépendantes ; pays proposés, précision de lieux et métier libre si nécessaire.
2. **Mobilité et langues** : déplacements depuis le domicile ou installation ; durée maximale de trajet et transports conditionnels ; niveaux de langue déclarés, permis détenus et autre autorisation. Aucun permis n’est déduit du choix voiture.
3. **Conditions** : disponibilité, contrats et quotité séparés, horaires variés ou grille hebdomadaire, conditions acceptées et attente salariale éventuelle structurée.
4. **Récapitulatif** : relecture modifiable et confirmation explicite. La création du compte et du profil durable est
   soumise à la vérification de l’adresse e-mail et à une confirmation POST.
   Voir [l’inscription candidat](CANDIDATE_EMAIL_REGISTRATION.md).

Les descriptions de parcours et l’envoi de fichier ne sont plus acceptés. Le lecteur brut et les tests introduits spécifiquement pour l’essai CV ont été retirés ; aucun changement du lecteur PDF/image employeur.

### Catalogue

API partagée `/api/occupations/`. ESCO et ROME restent indépendants : aucune équivalence présumée, sélection ROME ne sélectionnant pas ESCO. Références vérifiées côté serveur, dix maximum ; libellés canoniques au récapitulatif, catalogues ESCO 1.2.1 et ROME 26M10. Recherche en direct avec JavaScript, bouton serveur sans JavaScript. Sélections conservées entre recherches et langues. Les pannes et l’absence de résultat sont distinguées.

### Horaires

Source historique locale consultée : `forms/eures-beta/app.js`, module horaires variés/contraintes puis lundi–dimanche × matin/après-midi/soir/nuit. Site FT non accessible à la lecture directe au moment de la reprise : identité exacte avec la version en ligne non vérifiée. Nouveaux noms `schedule_preference` et `schedule_<day>`. Grille conditionnelle et présentation verticale sur mobile. Au moins un créneau si horaires précisés ; un jour vide reste non renseigné, sans conclusion d’indisponibilité. Réponses relues au récapitulatif.

### Accès et conservation

Le parcours est disponible dans tous les environnements, sans restriction
loopback ou mode démo. Les choix sont validés côté serveur, avec CSRF et jeton
de brouillon. La confirmation d'inscription est distincte du brouillon ; elle
crée un compte et un profil après vérification, selon le contrat d'inscription.
Le transport e-mail reste configuré séparément et protégé côté serveur.

Brouillon privé à la session, accès limité à 2 heures sans activité (délai remis à zéro à chaque page du parcours, avertissement 2 minutes avant avec bouton de prolongation) et suppression explicite possible. L’expiration est vérifiée lors d’une requête ; sans requête ultérieure, la ligne de session reste jusqu’au nettoyage technique Django. Ce délai ne constitue pas une purge planifiée.

Lors de la reprise d’un ancien brouillon, texte CV, sources d’extraction et champs supprimés sont retirés de la session active ; les réponses encore utiles (projet et préférences) sont conservées. La nouvelle structure recommence à la première étape pour relecture, avec un nouveau jeton. Cela ne constitue pas une purge des anciennes sessions inactives ou des sauvegardes techniques.

### Limites

La prolongation du brouillon utilise un POST protégé par CSRF et le jeton du
brouillon courant. Le navigateur annonce la réussite seulement après une
confirmation JSON explicite du serveur. Un brouillon expiré ou absent reçoit
un refus (409), sans recréer un brouillon ni annoncer une conservation fictive.
Les réponses déjà enregistrées en session sont conservées à l'identique ; les
champs en cours de saisie restent dans le formulaire du navigateur jusqu'à
leur validation. `make test-js` vérifie ces annonces, y compris une
réponse HTML ou dépourvue de confirmation.

FR/EN/DE, contrôles serveur des réponses conditionnelles, des choix incompatibles, des créneaux et des montants. Consulter la notice `/privacy/` et le contrat d’inscription pour la conservation. Coque et logos conservés ; aucun audit complet WCAG ni certification graphique. Les anciennes validations chiffrées ci-dessous décrivent des étapes historiques,
pas la validation de la version courante.

Validation de cette version : 232 tests PostgreSQL réussis, dont 18 tests ciblés candidat. Contrôles Django/migrations, traductions FR/DE, syntaxe JavaScript et formatage des templates réussis. Accueil simplifié vérifié dans le navigateur.


## Langues — composant employeur partagé

À la demande d’Eric, le module JavaScript employeur est réutilisé avec des formulations candidat : ajout/recherche/retrait de langues dans le catalogue ISO du navigateur et choix A1–C2 avec descriptions pratiques, sans test ni certification. Les trois listes fixes FR/EN/DE sont remplacées. Le candidat déclare son propre niveau, pas une exigence de poste ; une option permet de faire le point sur ses langues. Les codes et niveaux sont conservés en données structurées de session, limités à 20 langues, sans doublon et contrôlés côté serveur. Réponses facultatives ; sans JavaScript, possibilité de laisser à discuter.

Les anciennes réponses A1–C2 sont reprises à l’identique. « Langue maternelle » et « À discuter » ne deviennent jamais un niveau CECRL supposé ; elles restent à vérifier. Libellés de langue localisés dans le navigateur et codes ISO visibles sans JavaScript au récapitulatif. La sérialisation employeur existante reste inchangée.

Validation : 235 tests PostgreSQL réussis, dont 21 tests candidat ; vérification navigateur de recherche, ajout, choix de niveau et retrait d’une langue d’essai. Aucun enregistrement de la langue d’essai dans le brouillon utilisateur. Contrôles des traductions et de syntaxe JavaScript réussis.


## Cohérence entre grille et conditions acceptées

Les créneaux explicites proposent journée (matin/après-midi), soirée/nuit et week-end (samedi/dimanche), sans aucune déduction pour travail physique, transport, horaires variables ou jours fériés. Les propositions sont signalées et restent modifiables. Une correction manuelle reste prioritaire lors des changements ultérieurs de grille et après reprise du brouillon ; les choix existants antérieurs à cette fonctionnalité restent protégés.

Le candidat peut confirmer « Ce sont mes seules disponibilités ». Dans ce cas, les créneaux non cochés sont exclus ; une condition journée/soirée-nuit/week-end sans aucun créneau compatible produit une alerte immédiate et une erreur serveur à corriger. Sans cette confirmation, une case vide reste non renseignée, et ne produit pas une incompatibilité certaine. Ce contrôle détecte l’absence de toute intersection ; il ne certifie pas la compatibilité d’un horaire précis ou d’une offre. La proposition est effectuée dans le navigateur ; les incompatibilités et l’état des corrections sont contrôlés côté serveur. Sans JavaScript, le questionnaire reste saisissable et le contrôle serveur s’applique.

Validation des règles horaires : 237 tests PostgreSQL passent, dont 23 tests ciblés. Recette navigateur dans une session distincte : précochages, correction prioritaire, retrait de suggestion et alerte vérifiés.
