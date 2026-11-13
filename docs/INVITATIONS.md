# Invitations

## Application Django

Le domaine est regroupé dans `eures_beta/invitations/` : modèle, services,
formulaires, vues, routes, administration, e-mails, styles et tests. Les comptes
et l'authentification restent dans `users`.

Le modèle existant change d'application sans recréation de table ni copie de
données. `invitations.0001` et `users.0009` transfèrent son état Django et ses
métadonnées de permissions ; les identifiants, attributions, relations et liens
envoyés sont conservés. Le nom physique `users_invitation` reste explicite dans
le modèle pour éviter toute opération destructive. Le transfert est réversible ;
les migrations historiques restent inchangées. Voir
[le détail technique](../eures_beta/invitations/README.md).
`invitations.0002` assure aussi la fin du transfert lors d'une migration ciblant
cette application, avant la génération automatique des permissions.

## Templates des e-mails

Les templates sont classés par type de destinataire dans
`eures_beta/invitations/templates/invitations/emails/` : `employer/`, `candidate/` et
`adviser/`. Le premier message s’appelle `invitation.html`/`invitation.txt`,
avec un objet `invitation.subject` pour les employeurs et candidats. Une relance
utilise `reminder.*` ; chez les conseillers, le même template adapte le texte
selon le contexte. Les relances employeurs réutilisent le contenu de l’invitation.
Le rôle dans le nom du sous-dossier désigne le destinataire, pas l’expéditeur.

## Onglet conseiller « Inviter »

La recette locale Django est basée sur le sommet de la pile #187. Depuis le
tableau de bord `/accounts/dashboard/`, l’onglet **Inviter** s’ouvre par défaut. Il permet de préparer une invitation
employeur, candidat ou conseiller, puis de vérifier l’objet, le destinataire
et le rendu HTML avant confirmation. Prénom et nom sont facultatifs. Le CSV
UTF-8 accepte les séparateurs virgule et point-virgule et les colonnes
`email`, `prénom` (ou `prenom`) et `nom`. Un fichier contient au plus dix
destinataires, tous du même type. Les erreurs de saisie sont affichées avant
tout envoi, et les conflits détectés à l’envoi sont signalés par destinataire.

Le suivi affiche les invitations en attente d’envoi, sans réponse, expirées
ou acceptées. Une relance confirmée renouvelle le lien pour sept jours et
révoque le précédent. Les nouveaux envois et les relances partagent le
quota existant de dix opérations par conseiller et par heure.
La suppression révoque le lien d’une invitation non acceptée. L’invitation
d’un conseiller est ouverte à tous les conseillers connectés et actifs
et crée un compte conseiller ordinaire, sans accès à l’administration. Le candidat
invité peut terminer son questionnaire avec l’adresse déjà vérifiée par
l’invitation.

Les modèles génériques français Flask d’invitation et de relance pour candidats
et employeurs ont été adaptés à Django. Un modèle conseiller a été créé, faute
de modèle correspondant dans l’export. Le code conserve une version texte et
une version HTML. Le transport réel réutilise le SMTP commun, destiné à être
configuré pour Brevo. En recette locale, la boîte de test est
`.runtime/invitation-outbox/`. Elle contient des liens de test à usage unique.

L’onglet « Inviter » utilise le modèle court pour les invitations et relances
employeurs. Le premier envoi suit la langue de l’aperçu (français, anglais ou
allemand), puis la relance reprend la langue enregistrée. La signature reprend
le prénom, le nom et la structure du conseiller connecté, modifiables depuis
« Mon compte ».
Les logos EURES/ELA, France Travail, ADEM et Le Forem utilisent les ressources
du site, avec des adresses absolues dans le message envoyé.

`make translations-extract` extrait aussi les objets d’e-mail des templates
`.subject`. Sans cette extension explicite, une extraction suivie de compilation
retirerait leurs traductions et ferait revenir les objets en anglais.

Pour essayer le parcours, utiliser `make run PORT=9060` dans la copie locale
configurée, puis ouvrir `/accounts/test-accounts/`. Le conseiller
fictif permet de tester les trois types. `make test` couvre
l’aperçu, le CSV, le dépôt local, la confirmation et la révocation.

## Parcours employeur historique

Les conseillers actifs voient les comptes employeurs et les invitations
en attente sur `/accounts/dashboard/?tab=employers` (25 lignes par liste). L’ancienne route
`/adviser/invitations/new/` reste disponible pour le formulaire employeur
multilingue. Le tableau de
bord employeur reste en construction. Tous les conseillers voient les
comptes employeurs, sans périmètre individuel dans cette première version.

## Autorisations et données

Tout conseiller connecté et actif peut consulter et créer les invitations,
sans permission Django supplémentaire et même sans groupe. Le groupe historique
`employer-inviters` peut encore être synchronisé mais ne conditionne plus ces
actions. Cela ne donne aucun accès à l'administration Django.

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

Une adresse déjà inscrite ou invitée est signalée au conseiller connecté.
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

L'envoi reste désactivé par défaut. Le formulaire confirme l'enregistrement
de l'invitation avec le même texte, quelle que soit la configuration du transport.
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

`make test TESTS=tests.invitations.test_invitations` couvre droits, doublons, expiration, rejeux, CSRF,
traductions et simulation. `make test` vérifie les interactions avec le projet.

## Noms du modèle commun

`Invitation` couvre les trois types de destinataires. `sender` est le conseiller
qui invite ; `recipient_kind` est le type de compte prévu ; `recipient` est le
compte créé à l’acceptation (vide auparavant). Les relations inverses sont
`User.sent_invitations` et `User.invitation`.

`User.organization_name` contient un nom d’organisation facultatif, utilisé
avec le prénom et le nom pour composer le pied de l’e-mail. Ce champ n’est pas
une signature libre ni une relation vers une organisation métier.

La migration réversible `users.0008_invitation_names` renomme la table et les
colonnes existantes avec les opérations natives Django ; elle ne recrée aucune
invitation ni aucun compte. Identifiants, jetons, dates et relations sont conservés.
Les ContentTypes et permissions sont renommés en conservant leurs identifiants
et les attributions existantes. La synchronisation versionnée reste appliquée
au déploiement. L’URL publique et le sel de signature historiques restent inchangés.
