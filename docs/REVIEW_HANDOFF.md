# Clôture Albert et traitement conseiller

## Parcours

Après relecture et choix distinct de transmission, ou refus du poste/de
l’employeur, les réponses sont remises aux conseillers. Le candidat voit la
confirmation de sauvegarde, la prochaine étape et l’absence d’envoi à l’employeur.
Le dossier reste consultable après un accord comme après un refus de partage.

`CandidateOfferReview` conserve l’état de traitement, le conseiller responsable,
la version, la date de remise, l’empreinte et la synthèse courante.
`CandidateOfferReviewEvent` garde chaque remise et sa synthèse figée, les prises
en charge, libérations, reprises motivées et décisions, avec auteur/date/version.
La relation inverse est `review.events` ; `action` indique le type d'événement.
Les réserves et les conditions inconnues sont conservées. Il ne s’agit pas d’une
nouvelle interprétation générative des réponses ; l’avis Albert reste distinct.

Tous les conseillers actifs voient les dossiers. L’initiateur retrouve une alerte
dans son tableau de bord ; un email minimal est tenté après commit. Un collègue
peut prendre en charge un dossier libre ou reprendre un dossier avec un motif
interne. Les formulaires périmés ne peuvent ni écraser l’assignation ni enregistrer
une seconde décision. Une reprise change aussi le conseiller de la conversation
à trois existante, dont les autres participants restent inchangés.

Le responsable peut valider, demander un complément ou refuser. Chaque décision
exige une explication au candidat, distincte de la note interne. Le candidat lit
l’explication dans son dossier et reçoit une tentative d’email ; il peut répondre
à une demande de complément. Les notes internes ne passent dans aucun contexte
de page candidat, email candidat ou conversation employeur.
La validation exige un accord de transmission actuel et aucun refus du poste
ou de l’employeur. La conversation à trois conserve son consentement propre.
Un refus final concerne cette opportunité seulement et ne désactive pas le profil.

Toute modification pertinente invalide les actions sur l’ancien contexte.
Les réponses corrigées et le nouveau choix de partage produisent une nouvelle
remise ; les synthèses et décisions antérieures restent dans l’historique.

## Profil et refus répétés

Les exceptions à une offre ne changent jamais le profil. Un refus rapide d’une
condition compatible avec le profil ouvre une question explicite : exception pour
cette offre ou changement général ? Le choix est conservé dans une nouvelle
version de réponse ; le choix général ouvre seulement un brouillon à valider. Une proposition générale
Albert exige une preuve dans les paroles du candidat, une confirmation, puis la
relecture et la validation des formulaires habituels ; un brouillon n’est pas
une modification durable. Les changements concurrents du profil restent protégés.

Au troisième refus actuel d’une même condition sur trois offres distinctes,
`candidates.CandidateProfileReviewSuggestion` propose de conserver ou revoir le profil. Il garde
les identifiants des réponses/offres justificatives et la résolution datée.
Le modèle et son administration appartiennent à `candidates` ; la détection des
refus et leur validation restent dans `matching`, avec les mêmes règles.
Le comptage utilise la dernière réponse de chaque offre, encore valide pour les
déclarations actuelles du profil. Une répétition sur la même offre, une réponse corrigée ou un
contexte devenu périmé ne compte pas. L’identité est exacte : type de condition
et exigence enregistrée, hors caractère obligatoire ; aucune équivalence sémantique
n’est inventée. Poste et employeur sont exclus des préférences générales.
Un choix de conservation ne modifie aucun champ ; « revoir » ouvre le formulaire
sans modification automatique. Une proposition devenue injustifiée n’est plus
présentée et son ancien formulaire est refusé.

## Migration, transport et recette

Migrations additives `matching.0018–0019` : anciennes réponses, accords et identifiants
préservés. Les anciens dossiers restent en attente ; un candidat ayant déjà
terminé peut remettre ses réponses actuelles par une action explicite. Aucun
email de rattrapage, consentement ou décision n’est fabriqué par migration.
`0019` renomme seulement les contraintes et index du suivi pour respecter les noms
des modèles, après création des clés étrangères différées ; aucune table recréée.
`0020` renomme le journal `CandidateOfferReviewAction` en `CandidateOfferReviewEvent`,
sa table, ses objets PostgreSQL et les permissions associées en place. Les lignes,
identifiants, dates, relations et séquence sont conservés, y compris au retour arrière.
Les migrations publiées `0018–0019` restent inchangées.
`matching.0021` déplace la table du second modèle en place et renomme ses objets
PostgreSQL, son type de contenu et ses permissions ; `candidates.0010` adopte
ensuite son état sous le nom `CandidateProfileReviewSuggestion`, sans créer de table.
Le graphe impose cet ordre et le retour vers `matching.0020` annule aussi
`candidates.0010`. Les données, identifiants, relations et séquence sont conservés
dans les deux sens ; les migrations précédentes ne sont pas réécrites.
Le retour arrière conserve les données préexistantes, mais retire les nouveaux
champs et tables : sauvegarder le nouvel historique avant un retour en exploitation.

L’événement est l’alerte durable ; son état de transport indique pending, sent,
failed ou disabled. `sent` indique l’acceptation par le service, pas la livraison.
SMTP reste synchrone après commit, sans file de relance durable : une interruption
peut laisser une tentative pending. L’alerte et les messages restent dans l’app.

Tests : `make test TESTS='tests.introductions.test_review_workflow tests.introductions.test_review_concurrency tests.introductions.test_review_workflow_migration'`.
Suite complète : `make test`, avec `ALBERT_SIMULATED=0` et
`DEMO_ACCOUNTS_ENABLED=0` dans le `.env` de test : chaque test choisit son
scénario et simule les frontières réseau. Vérifier FR/EN/DE, sécurité, templates et traductions
avec les commandes communes. Les frontières réseau sont simulées dans les tests.
La recette locale utilise une base fictive dédiée, Albert simulé et les emails
désactivés ; aucune configuration de déploiement n’appartient à ce lot public.
