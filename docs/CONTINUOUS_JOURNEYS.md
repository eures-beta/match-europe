## Mise à jour — 9 novembre 2026

Les compétences des formulaires sont actives par défaut dans tous les environnements. Les e-mails réels, les adresses ordinaires et les connexions distantes ne désactivent plus le parcours. Les comptes et leurs offres/profils conservent leurs droits de propriété. Le candidat vérifie son e-mail avant le questionnaire via le parcours commun ; aucun raccourci de confirmation dans le navigateur. Les simulations Albert sont explicites et ne sont plus imposées par l’activation des compétences. Les sources officielles peuvent être préparées ou lues depuis les archives vérifiées dans tous les environnements. Les anciennes limites ci-dessous sont historiques et remplacées.

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

Migration additive `candidates.0006_candidateprofile_occupation_skills`, après
les compétences du profil et la vérification email préalable : champ
JSON dédié `occupation_skills`, vide pour les anciens profils. Même validation
dans le questionnaire, l’enregistrement après relecture et le modèle durable. Chaque clé
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

Le brouillon conserve les deux heures d’inactivité du parcours courant, le lien
de vérification une heure et le profil la durée de la notice existante ; cette
migration n’ajoute pas de purge automatique. Les suggestions de
référence publiques restent distinctes des déclarations individuelles.

## Protections de la recette

Les compétences sont intégrées aux parcours dans tous les environnements. Le POST
`/api/occupation-skills/` est protégé contre CSRF ; employeur authentifié ou candidat actif connecté avec
son propre brouillon et son jeton de session. Les résultats ne sont pas accessibles aux autres rôles.
Échec ou expiration : message explicite et nouvel essai possible, pas de choix
inventé ni d’effacement du brouillon. Réponses navigateur périmées ignorées.

La recette force Albert simulé, y compris si une clé locale était présente.
L’import employeur utilise alors l’extraction déterministe existante et les
compétences hors fiches une sélection déterministe dans les relations officielles.
Ce fonctionnement teste le parcours ; il ne démontre pas la pertinence d’Albert.
Le composant le signale. Aucun coût Albert ni e-mail réel.

La confirmation candidat locale est privée à la session qui vient de préparer
la demande, uniquement pour une adresse `.invalid`, en local ou recette HTTPS explicitement activée. Un POST explicite simule
la réception, puis le POST de confirmation habituel active le compte, avant le
questionnaire. Le profil n’est créé qu’après sa relecture et validation. Aucun lien
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

`make run PORT=9040` ouvre l’accueil sur le port choisi. Pour cet essai,
configurer explicitement `ALBERT_SIMULATED=1`, `TEST_ACCOUNTS_ENABLED=1`,
`DJANGO_ENVIRONMENT=local`, `EMAIL_DELIVERY_ENABLED=0`
dans le `.env` du worktree. Le port ne sélectionne aucun parcours ni simulation.
Aucun déploiement.

Employeur : choisir le compte de test depuis le bandeau de l’accueil, décrire une
offre fictive, choisir un résultat ESCO, sélectionner ses compétences, finir les
conditions, le profil, la mobilité et la relecture. Enregistrer le contact et les
pratiques de réponse. Rouvrir l’offre depuis le tableau de bord et vérifier la
conservation des choix. Tester une fiche parmi les 50 et un métier hors fiches.

Candidat : depuis l’accueil, indiquer une adresse `.invalid`, utiliser la
simulation privée de réception et confirmer l’email. Dans le questionnaire,
chercher un métier ESCO (exemple hors fiches : photographe), sélectionner ses
compétences, poursuivre mobilité/conditions/relecture et enregistrer. Vérifier le
profil et la modification. Le mode sans métier reste disponible séparément
dans le même questionnaire. Tous les essais utilisent des réponses fictives.

Sans JavaScript, le questionnaire classique fonctionne et n’invente aucune
compétence ; les propositions par métier ne sont pas disponibles. Les données
déjà enregistrées restent soumises à la validation serveur.

Contrôles : `make test TEST_ARGS='-k continuous -k skill_source_prepare'`, `make test-js`, `make test`,
`make check`, `make format-check`, `make format-html-check`,
`make format-js-check`, `make check-js`, `make translations-check`,
`make translations-compile`. L’évaluation réelle Albert, la publication en PR,
la fusion et le déploiement de production restent distincts de cet essai.

## Recette distante autorisée

La recette doit être configurée extérieurement au dépôt avec
`DJANGO_ENVIRONMENT=preview`, HTTPS, `TEST_ACCOUNTS_ENABLED=1`,
`EMAIL_DELIVERY_ENABLED=0` et `ALBERT_SIMULATED=1`. La simulation est explicite,
sans clé requise. Les migrations et le peuplement fictif restent des opérations
séparées ; seuls les comptes fictifs autorisés sont peuplés.

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
