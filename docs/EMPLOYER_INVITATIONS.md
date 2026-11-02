# Invitations employeurs

Les conseillers actifs habilités voient les comptes employeurs et les invitations
en attente sur `/accounts/dashboard/` (25 lignes par liste). Le bouton d'invitation
ouvre `/accounts/employers/invite/` : e-mail et langue du message. Le tableau de
bord employeur reste en construction. Tous les conseillers habilités voient les
comptes employeurs, sans périmètre individuel dans cette première version.

## Autorisations et données

Le groupe versionné `employer-inviters` possède les droits d'ajout et consultation
d'`EmployerInvitation`. Il est réconcilié au déploiement pour les conseillers
actifs ; les nouveaux conseillers le reçoivent dès leur création. Cela ne donne
aucun accès à l'administration Django. Les vues vérifient aussi rôle et activité.

La migration additive `users.0004_employerinvitation` crée une table : e-mail
normalisé unique, langue, conseiller à l'origine, dates de création, expiration,
acceptation, compte créé et date d'envoi effectif éventuel. Un identifiant aléatoire
de renouvellement invalide les anciens liens. Les jetons sont signés, sans e-mail
dans leur contenu, et ne sont pas conservés en clair en base.

GET nettoie l'URL avec `no-referrer`, sans créer de compte. Une confirmation POST
avec CSRF accepte l'invitation et connecte le destinataire. Le rôle est toujours
employeur actif, sans mot de passe utilisable, sans staff ni superutilisateur.
La transaction verrouille l'invitation pour empêcher sa double consommation. Un
compte existant n'est jamais modifié ni promu. La désactivation du conseiller
invalide ses invitations en attente.

Une adresse déjà inscrite ou invitée est signalée au seul conseiller habilité.
Une invitation expirée peut être renouvelée via le même formulaire, ce qui
invalide ses anciens liens. Limite partagée entre navigateurs : dix invitations
ou renouvellements par conseiller et heure. Pas de renvoi d'invitation encore
valide dans cette première version. Les invitations restent conservées pour
retrouver qui les a créées ; aucune suppression automatique n'est ajoutée.

## Délais

- Connexion d'un compte existant : une heure, usage unique.
- Invitation initiale : sept jours, usage unique, avec expiration en base.
- Session : trente jours d'inactivité, prolongés par les requêtes actives.

Le nouveau délai de connexion s'applique aussi aux jetons déjà émis mais pas
encore consommés. Le lien initial reste distinct de la connexion habituelle,
qui ne crée jamais de compte : aucune inscription autonome n'est ouverte.

## Simulation privée des messages

Aucun prestataire n'est configuré et l'envoi reste désactivé par défaut. Le
formulaire réserve l'invitation et annonce explicitement l'absence d'envoi.
Un opérateur peut utiliser la référence UUID affichée :

```bash
make invitation-email \
  INVITATION=UUID \
  ORIGIN=https://hote-autorise
```

Pour un compte existant actif :

```bash
make login-email \
  EMAIL=reviewer@example.invalid \
  ORIGIN=https://hote-autorise \
  LANGUAGE=fr
```

Ces commandes utilisent uniquement la base du `.env`, ne créent aucun compte
et n'envoient rien. Elles n'allongent pas la durée de l'invitation. Leur sortie
contient un lien secret : ne pas la committer ou la publier dans une issue ou des
logs partagés. Origine HTTPS autorisée exigée ; HTTP est réservé au loopback
avec DEBUG. Aucun lien n'est exposé dans les pages du conseiller.

Lorsque l'envoi Django sera configuré et activé séparément, le même message sera
envoyé. Les tests le simulent dans une boîte en mémoire. Les échecs sont annoncés
sans journaliser de contenu personnel ; l'opérateur peut simuler le message.

`make invitations-test` couvre droits, doublons, expiration, rejeux, CSRF,
traductions et simulation. `make test` vérifie les interactions avec le projet.
