## 9 novembre 2026 — transport commun sans exclusion d’environnement

L’envoi dépend de sa configuration explicite (`EMAIL_DELIVERY_ENABLED`, `LOGIN_EMAIL_ENABLED`, origine HTTPS de confiance et transport SMTP), jamais du nom de l’environnement. L’envoi reste désactivé par défaut. Les tests simulent le transport et les outils de comptes fictifs restent incompatibles avec l’envoi réel. Aucune configuration distante ni aucun e-mail réel n’est modifié par cette correction. Cette décision remplace les anciennes mentions « production uniquement » ci-dessous.

# Questionnaire ouvert et confirmation candidat

L’écran de demande de confirmation est identique avec ou sans transport d’e-mails
configuré. L’absence d’envoi ne rajoute ni avertissement de recette ni lien secret
à la page ; la vérification de l’adresse reste obligatoire avant toute création.

## 9 novembre 2026 — remplacement de la proposition email préalable

Cette version remplace la PR #164 abandonnée : aucun compte ni email n’est
nécessaire pour commencer. L’accueil propose le questionnaire et une connexion
pour retrouver un profil existant. L’email est demandé à la dernière étape.

Les seules données métier durables restent `users.User` et
`candidates.CandidateProfile`. Les réponses en attente de vérification sont
conservées une heure dans des lignes dédiées de `django_session`, distinctes
des sessions de navigation et sans authentification. Le lien signé ne contient
que deux UUID, jamais une clé de session de navigateur, l’email ou les réponses.
Le brouillon du navigateur reste disponible pendant son délai d’inactivité de
deux heures ; ouvrir le lien sur un autre appareil retrouve aussi les réponses.

Après le POST de vérification protégé par CSRF :

- nouvelle adresse : création atomique du compte candidat et du profil ;
- candidat actif sans profil : création du profil sur le compte existant ;
- candidat avec profil : connexion puis comparaison de l’ancien profil et des
  nouvelles réponses, sans modification automatique. Un second POST explicite
  permet de conserver le profil ou de le remplacer. La proposition expire après
  deux heures et est liée au compte connecté. Une modification concurrente du
  profil impose une nouvelle comparaison ;
- compte inactif ou autre rôle : explication après vérification seulement,
  aucun compte modifié. Les réponses sont remises dans le brouillon pour
  permettre d’utiliser une autre adresse.

Plusieurs demandes indépendantes pour le même email sont possibles dans les
limites anti-abus existantes ; aucune ne remplace les réponses d’une autre.
La page publique reste neutre sur l’existence d’un compte. GET ne confirme rien,
le jeton est retiré de l’URL et un POST ne peut le consommer qu’une fois.

La migration `0004_confirmation_sessions` transfère les demandes existantes
(réponses, dates, UUID et nonce conservés), puis supprime leur ancienne table.
Les liens déjà envoyés restent valables pendant leur échéance initiale. Aucun
compte ou profil existant n’est supprimé. Un retour à l’ancien schéma échoue
explicitement s’il ne peut représenter plusieurs demandes du même email, au lieu
de perdre des données. Nettoyer ou terminer ces demandes avant un tel rollback.

`make candidate-email EMAIL=personne@example.invalid ORIGIN=http://127.0.0.1:9035`
simule en privé le message de la demande la plus récente pour cette adresse ;
ne jamais publier le lien de connexion. `make candidate-registration-cleanup`
compte les paquets expirés ; `CLEANUP_ARGS=--apply` les supprime sans toucher aux
sessions de navigation ni aux profils. Le nettoyage Django usuel des sessions
expirées est également compatible. Il n’y a pas de tâche de purge nouvellement
installée : l’expiration interdit l’accès sans garantir l’effacement immédiat.

Le backend email commun et son activation explicite sont conservés. Aucun
transport, secret ou réglage distant n’est ajouté par cette PR.
Les textes et les écrans de comparaison existent en FR/EN/DE. Aucun matching,
partage conseiller ou inscription employeur n’est ouvert.

## Historique — premier lot P1 (remplacé sur les points décrits ci-dessus)

## Périmètre et activation

Lot empilé sur #131. À la demande d'Eric, les quatre étapes du questionnaire
peuvent préparer un compte et une fiche après confirmation d'e-mail, puis
permettre au candidat de consulter et modifier ses propres réponses.

Le parcours est disponible dans tous les environnements, sans interrupteur
candidat ni restriction aux adresses fictives. L’ouverture en production a été
explicitement autorisée par dejafait. Les protections de confirmation et de
propriété restent identiques partout.

L’envoi suit le backend Django protégé commun à la connexion et aux invitations :
e-mails réels uniquement en production correctement configurée. En local et en
recette, l’opérateur récupère le message par la commande privée ; aucun e-mail
réel n’est transmis. Une indisponibilité du transport ne rend pas les liens publics.

## Parcours

1. Questionnaire anonyme en quatre étapes, ESCO/ROME toujours indépendants.
2. Dernière étape : nom d'affichage, email obligatoire, relecture et lien
   vers la notice. La case constate une lecture, pas une nouvelle base juridique.
3. Revalidation serveur de toutes les étapes ; seuls les champs du profil sont
   conservés dans une demande temporaire. Aucun compte n'existe à ce stade.
   Le brouillon de session est retiré après la demande.
4. Le transport protégé envoie l’e-mail lorsqu’il est configuré ; sinon,
   l’opérateur le simule en privé. Le lien signé contient un identifiant et
   un nonce, jamais les réponses ou l'adresse email. GET mémorise le lien dans
   la session et redirige vers une URL propre ; il ne crée rien.
5. Confirmation POST avec CSRF : verrou PostgreSQL, compte candidat et fiche
   créés atomiquement, demande supprimée, session connectée et renouvelée.
   Un lien consommé, falsifié ou expiré ne crée ni compte ni profil.
6. `/candidate/profile/` est réservé au candidat propriétaire. Modification par
   un POST protégé, puis questionnaire prérempli et nouvelle validation complète.
   L'email du compte est affiché désactivé et n'est pas modifié par ce parcours.

Un compte existant (y compris inactif, conseiller ou employeur) n'est ni converti
ni remplacé. Un candidat existant utilise la connexion habituelle pour retrouver
son profil. Un compte candidat actif sans fiche peut recevoir sa première fiche
après la même vérification email, sans créer de second compte. Une demande non
confirmée existante n'est pas remplacée par un autre
visiteur. La page de résultat reste neutre et n'affiche ni adresse ni jeton.
Les limites PostgreSQL communes par adresse et IP s'appliquent aux soumissions.

## Données et conservation

- `candidates.CandidateRegistration` : UUID, nonce, email normalisé, langue,
  réponses validées, création et échéance. Migration additive `0002`.
- Délai de confirmation : **une heure**, contrôlé à la fois par signature et date
  stockée. Ce délai ne concerne pas les invitations employeurs ni les profils.
- Après confirmation, les réponses temporaires disparaissent de la demande.
  Les demandes expirées sont effacées lors d'une nouvelle demande ou par la
  commande de nettoyage. Pas de tâche planifiée installée : l'échéance d'accès
  ne garantit donc pas la purge physique exactement à la minute prévue.
- `CandidateProfile` reçoit par `0003` une date de vérification email, la date
  de lecture déclarée et la version de la notice. Les profils antérieurs gardent
  des valeurs vides : aucune vérification ou lecture rétroactive n'est inventée.
- L'administration de la demande est en lecture seule, limitée aux UUID/dates ;
  ni email, réponse ou nonce ne sont exposés dans ses listes ou détails.
- La migration inverse de `0002` supprime la table des demandes et son contenu ;
  celle de `0003` retire les métadonnées de vérification/notice. Le profil et les
  comptes préexistants sont conservés. Aucun retour arrière réel automatique.

Les 12 mois après dernier contact utile restent la règle de référence pour le
profil confirmé, issue de Flask et de la notice commune. Ce lot n'implémente pas
sa purge automatique et ne prétend pas que `updated_at` est un dernier contact
utile. Ces limites restent à traiter séparément : définir ce jalon, implémenter la
suppression, compléter les mentions juridiques et superviser les nettoyages.
Le raccordement au transport de production commun est désormais inclus.

## Essayer et vérifier

- `make install-test` et `make install-quality` pour ce worktree ; `.env` et
  PostgreSQL dédiés, puis `make migrate`.
- `make candidate-registration-run` démarre le serveur local sur le port 9035 :
  `/candidate/prepare/?lang=fr` (EN/DE disponibles).
- À la fin du questionnaire, `make candidate-email EMAIL=personne@example.invalid
  ORIGIN=http://127.0.0.1:9035` imprime un email simulé privé. La commande ne
  transmet rien. Ne pas publier sa sortie : le lien autorise une connexion.
- `make candidate-registration-cleanup` compte sans effacer ;
  `make candidate-registration-cleanup CLEANUP_ARGS=--apply` efface uniquement
  les demandes expirées, jamais les profils ou comptes.
- `make candidate-registration-test` : création atomique, POST/CSRF, expiration,
  rejeu, conflit de compte et de demande, droits, édition, traduction, nettoyage,
  simulation email et confirmation concurrente PostgreSQL.
- `make candidate-test`, `make test`, `make check`, `make users-upgrade-test`,
  `make format-check`, `make format-html-check`, `make translations-check`.

La validation automatisée utilise uniquement des données fictives et des
transports simulés. Aucun appel de matching ni partage conseiller/employeur
n’est ajouté. Aucune fusion ou modification de base de production n’a été
effectuée pour cette ouverture du code.
