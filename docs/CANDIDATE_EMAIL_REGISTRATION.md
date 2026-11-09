## 9 novembre 2026 — transport commun sans exclusion d’environnement

L’envoi dépend de sa configuration explicite (`EMAIL_DELIVERY_ENABLED`, `LOGIN_EMAIL_ENABLED`, origine HTTPS de confiance et transport SMTP), jamais du nom de l’environnement. L’envoi reste désactivé par défaut. Les tests simulent le transport et les outils de comptes fictifs restent incompatibles avec l’envoi réel. Aucune configuration distante ni aucun e-mail réel n’est modifié par cette correction. Cette décision remplace les anciennes mentions « production uniquement » ci-dessous.

# Candidat : vérifier l’email avant le questionnaire

Depuis l’accueil candidat, `/candidate/start/` demande l’adresse email avant toute
réponse métier. Le message public reste identique pour une adresse nouvelle,
existante, désactivée ou limitée par l’anti-abus. Il ne révèle pas l’existence des
comptes. Aucun mot de passe n’est demandé.

## Nouveau candidat

Une soumission valide crée un `users.User` de rôle candidat **inactif**, sans
mot de passe utilisable et sans profil. Trois champs d’authentification portent
le nonce de vérification, son échéance d’une heure et la langue du message.
Le lien signé est personnel : GET le place brièvement en session et nettoie
l’URL ; POST avec CSRF l’utilise une seule fois, active le compte et connecte le
navigateur. Le verrou PostgreSQL empêche deux activations simultanées.

Le questionnaire n’est accessible qu’à un candidat actif connecté. Il conserve
ses réponses en session privée pendant deux heures sans activité, avec
avertissement et prolongation. Le brouillon est lié à l’identifiant du compte :
un changement de compte ne donne pas accès au brouillon précédent. L’email
vérifié est affiché en lecture seule lors du récapitulatif.

La validation finale crée `candidates.CandidateProfile`, ou met à jour celui du
candidat connecté, sans créer un second compte ni un second profil. Le compte
porte l’email ; le profil porte les réponses métier et la lecture de la notice.
La connexion avant saisie établit la vérification de l’email pour ce parcours.
Aucun rapprochement ou partage avec un employeur n’est déclenché.

## Compte existant

Un compte actif reçoit le lien de connexion habituel, quel que soit son rôle.
Après connexion, un candidat retrouve son profil ou le questionnaire si le profil
n’existe pas encore. Un autre rôle reste inchangé ; une tentative d’accès au
parcours candidat explique qu’il faut utiliser une autre adresse. Les profils
existants ne sont jamais modifiés par la demande anonyme d’un lien.

Un compte désactivé n’est jamais réactivé par cette entrée, sauf s’il porte encore
le marqueur explicite de vérification candidat en attente. Une demande répétée
conserve le nonce et les données ; après expiration, une nouvelle demande peut
renouveler le lien. Les limites d’envoi communes restent appliquées.

## Deux modèles et migration

Le modèle temporaire `CandidateRegistration` est supprimé par une migration
supplémentaire, après les migrations de la PR parente. Les demandes préexistantes
sont transférées vers les comptes et profils sans marquer leurs emails comme
vérifiés. En cas de collision avec un autre rôle ou un profil existant, la
migration s’arrête et sa transaction est annulée : aucune donnée n’est écrasée.
Les anciens liens de confirmation doivent être redemandés après la migration.
Le retour arrière exige d’abord de traiter les comptes en attente ; la migration
refuse une inversion qui les laisserait sans procédure de vérification.

`make candidate-registration-cleanup` compte les comptes candidats inactifs en
attente dont le délai est dépassé. `CLEANUP_ARGS=--apply` les supprime avec leurs
éventuels profils associés ; ne touche pas aux comptes actifs ni aux comptes
simplement désactivés par un opérateur. Aucune purge planifiée n’est installée.
La conservation du profil confirmé reste celle de la notice, avec purge métier
à mettre en œuvre séparément.

## Recette et validation

`make candidate-registration-run` démarre le serveur local. `make candidate-test`
et `make candidate-registration-test` utilisent PostgreSQL ; `make test` valide
le socle complet. `make candidate-email EMAIL=… ORIGIN=…` affiche en privé un
message simulé, sans envoi. Sa sortie contient un secret de connexion : ne pas
la publier dans une PR, une issue ou des logs partagés.

Local et recettes utilisent le backend protégé sans emails réels. Le sélecteur
de comptes fictifs propose aussi un candidat pour tester le questionnaire et la
reprise du profil sans SMTP. La vérification email complète utilise la commande
privée de simulation ; un lien d’activation n’est jamais affiché publiquement.
Le sélecteur reste interdit en production. En production, les messages passent
par le backend email commun, avec ses réglages d’envoi explicites.
