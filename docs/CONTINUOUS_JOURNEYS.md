# Recette locale continue de la pile de PR

## Périmètre autorisé le 7 novembre 2026

Eric veut tester les évolutions encore dans la pile de PR depuis les parcours
habituels. Il confirme le raccordement employeur et candidat. Base vérifiée sur
GitHub : PR #157, `da5b1c4`, qui hérite de #156, #155, #154 et de la pile antérieure.
Branche locale `codex/continuous-skills-journeys` ; Eric autorise ensuite sa publication dans une nouvelle PR, une recette jetable
de sept jours et la fermeture de la recette de #157. Aucune fusion autorisée.

Le formulaire employeur conserve la préparation d’offre, les cinq étapes de
relecture, le contact et les pratiques de réponse par compte. Après un choix
ESCO, le composant commun propose les compétences dans le même formulaire.
Les 50 fiches sont réutilisées ; un autre métier ESCO utilise le service et le
cache versionné de #157. ROME et les intitulés personnels restent indépendants.
Les choix ne sont jamais présélectionnés, obligatoires, ni transformés en score.
Les plafonds existants sont cinq compétences et trois savoir-être par métier.
Les métiers hors fiches ne reçoivent pas de savoir-être inféré.

Le candidat peut conserver le parcours sans métier de #156, inchangé dans ses
règles 10/5/3. En mode métier, ses choix sont reliés à chaque URI ESCO explicitement
retenue. Le passage au mode ouvert efface ces déclarations par métier. Les choix
restent visibles dans la relecture, après confirmation, dans le profil privé,
et lors de sa modification, avec libellés officiels FR/EN/DE.

## Données et validation

Migration additive `candidates.0005_candidateprofile_occupation_skills` : champ
JSON dédié `occupation_skills`, vide pour les anciens profils. Même validation
dans le questionnaire, la demande temporaire et le modèle durable. Chaque clé
est un métier sélectionné ; compétences et savoir-être sont vérifiés côté serveur
contre les fiches ou les relations officielles ESCO, sans appel réseau lors de
la validation. URI, doublons et plafonds sont contrôlés. Le serveur fixe la version.
Le résumé affiche des libellés et non des identifiants bruts.

Employeur : `occupationSkills` dans le JSON existant de l’offre, avec la même
validation. Conservation à l’enregistrement, consultation, modification et
duplication. Changer l’intitulé dans l’édition existante retire le rapprochement
métier précédent et les choix associés ; aucune déclaration n’est transférée à
un autre métier. Les droits par propriétaire/établissement et la révision restent
contrôlés par les vues existantes. Administration candidat toujours limitée aux
métadonnées ; références de #157 toujours en lecture seule.

Les durées de brouillon, demande temporaire et profil restent celles du parcours
existant ; cette migration n’ajoute pas de purge automatique. Les suggestions de
référence publiques restent distinctes des déclarations individuelles.

## Protections de la recette

`CONTINUOUS_SKILLS_ENABLED=0` par défaut. Activation autorisée en local ou preview, sans e-mail réel. Le POST
`/api/occupation-skills/` exige le loopback réel en local, ou HTTPS et le mode
partagé explicite en preview,
protégé contre CSRF ; employeur authentifié ou brouillon candidat actif avec
son jeton de session. Les résultats ne sont pas accessibles aux autres rôles.
Échec ou expiration : message explicite et nouvel essai possible, pas de choix
inventé ni d’effacement du brouillon. Réponses navigateur périmées ignorées.

La recette force Albert simulé, y compris si une clé locale était présente.
L’import employeur utilise alors l’extraction déterministe existante et les
compétences hors fiches une sélection déterministe dans les relations officielles.
Ce fonctionnement teste le parcours ; il ne démontre pas la pertinence d’Albert.
Le composant le signale. Aucun coût Albert ni e-mail réel.

La confirmation candidat locale est privée à la session qui vient de préparer
la demande, uniquement pour une adresse `.invalid`, en local ou recette HTTPS explicitement activée. Un POST explicite simule
la réception, puis le POST de confirmation habituel crée le profil. Aucun lien
secret n’est affiché, aucun accès à une boîte commune et aucun contournement
de vérification d’adresse réelle. En preview elle exige le mode partagé HTTPS ; elle reste interdite en production.

Les comptes fictifs existants peuvent rouvrir leurs offres depuis le tableau de
bord dans cette recette. Les offres sans établissement restent accessibles à
leur propriétaire uniquement. Aucun élargissement des accès de production.

## Lancer et essayer

Environnement et base PostgreSQL propres à ce dossier : `make install-test`,
`make install-quality`, `make install-js`, `make db-create`, `make migrate`.
Installer les trois archives officielles épinglées dans `.runtime/catalog-sources/`
selon `ALBERT_SKILLS.md`, puis `make skills-source-check`.
Préparer les seuls comptes fictifs avec `make test-accounts-seed`, après activation
locale explicite de `TEST_ACCOUNTS_ENABLED=1`.

`make continuous-run` ouvre l’accueil sur le port 9040. Le port 9039 conserve
l’ancienne recette séparée et n’est pas la recette continue. Aucun déploiement.

Employeur : choisir le compte de test depuis le bandeau de l’accueil, décrire une
offre fictive, choisir un résultat ESCO, sélectionner ses compétences, finir les
conditions, le profil, la mobilité et la relecture. Enregistrer le contact et les
pratiques de réponse. Rouvrir l’offre depuis le tableau de bord et vérifier la
conservation des choix. Tester une fiche parmi les 50 et un métier hors fiches.

Candidat : depuis l’accueil, choisir le questionnaire, chercher un métier ESCO
(exemple hors fiches : photographe), sélectionner ses compétences, poursuivre
mobilité/conditions/relecture puis indiquer une adresse `.invalid`. Utiliser
la simulation privée de réception et confirmer l’enregistrement. Vérifier le
profil et la modification. Le mode sans métier reste disponible séparément
dans le même questionnaire. Tous les essais utilisent des réponses fictives.

Sans JavaScript, le questionnaire classique fonctionne et n’invente aucune
compétence ; les propositions par métier ne sont pas disponibles. Les données
déjà enregistrées restent soumises à la validation serveur.

Contrôles : `make continuous-test`, `make continuous-ui-test`, `make test`,
`make check`, `make format-check`, `make format-html-check`,
`make format-js-check`, `make check-js`, `make translations-check`,
`make translations-compile`. L’évaluation réelle Albert, la publication en PR,
la fusion et le déploiement de production restent distincts de cet essai.

## Recette distante autorisée

La recette doit être configurée extérieurement au dépôt avec
`DJANGO_ENVIRONMENT=preview`, `ME_SHARED_DEMO=1`, HTTPS,
`CONTINUOUS_SKILLS_ENABLED=1`, `SKILLS_ALBERT_ENABLED=1`,
`ALBERT_IMPORT_ENABLED=1`, `TEST_ACCOUNTS_ENABLED=1` et les e-mails réels
désactivés. Albert est forcé en simulation par le raccordement, sans clé requise.
Le pilote séparé reste désactivé. Les migrations et le peuplement fictif suivent
les mécanismes de recette existants ; seuls les comptes .invalid sont admis.

Avant le démarrage, préparer les sources officielles avec
`make continuous-source-prepare`, puis collecter les statiques. La commande
Django correspondante peut être utilisée dans le hook de construction privé.
Les trois exports publics sont téléchargés avec une limite de taille, un délai
et une empreinte épinglée, puis contrôlés avant promotion atomique. Cette étape
n’appelle pas Albert. Elle ajoute environ 27 Mo d’archives et prépare des fichiers
par métier contrôlés par empreinte, soit environ 70 Mo au total par instance.
Les requêtes ne chargent que les références du métier demandé. Une recette
sans cette préparation échoue explicitement plutôt que charger tous les exports
en mémoire sur la petite instance.

Le label de durée de la PR ouvre et ferme la recette selon le contrôleur privé ;
il ne fusionne pas de code. La recette de #157 doit être désactivée après
vérification de la nouvelle. Aucun réglage de production n’est modifié.

Pour cette recette continue uniquement, les connexions PostgreSQL sont réutilisées
pendant 60 secondes avec contrôle de validité et délai de connexion de 10 secondes.
La configuration reste un worker et quatre threads, sans augmentation de plan.
Les résumés de requête ajoutent le temps CPU et le délai avant le premier SQL,
sans texte SQL ni donnée saisie. Ces mesures distinguent une attente de connexion
d’un traitement CPU ; elles ne constituent pas à elles seules une preuve de cause.
