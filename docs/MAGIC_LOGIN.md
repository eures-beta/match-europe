# Connexion par lien magique

Le bouton commun « Se connecter » mène à `/accounts/login/`, en FR/EN/DE.
Les comptes existants conseiller et employeur utilisent le même écran. Aucune
adresse saisie ne crée de compte : inscriptions et invitations restent fermées.

## Bibliothèque et sécurité

Les jetons sont générés et vérifiés par
[django-sesame](https://django-sesame.readthedocs.io/en/stable/howto.html).
Ils expirent après une heure, sont invalidés après une connexion, un changement
d’e-mail ou une désactivation. La consommation est sérialisée par un verrou
PostgreSQL sur l’utilisateur. Le GET nettoie l’adresse puis affiche une
confirmation ; seul le POST protégé par CSRF ouvre la session. Un scanner de
courrier ne consomme donc pas le lien simplement en l’ouvrant.

La redirection portant le jeton utilise `no-referrer`. La page suivante, dont
l’URL est nettoyée, utilise `same-origin` : les informations d’origine restent
disponibles pour la protection CSRF HTTPS, sans référent envoyé aux sites tiers.
Appliquer `no-referrer` au formulaire empêche notamment Chrome de le confirmer
(`Origin: null`, puis 403) ; le test HTTPS et une vérification navigateur couvrent
cette régression. L’URL courte seule ne permet pas de se connecter : le jeton
reste dans la session serveur associée au cookie du navigateur jusqu’au POST.

La session Django reste valable 30 jours depuis la dernière requête, y compris
après fermeture du navigateur. Se déconnecter sur un appareil partagé. Les anciens
cookies du backend à mot de passe ne sont plus acceptés. La colonne `password`
reste celle du modèle Django standard, mais aucun backend de connexion par mot de
passe ni écran de réinitialisation n’est activé. L’administration utilise le même
lien ; ses permissions staff restent exigées. La création administrative propose
des comptes sans mot de passe.

Le message est identique pour une adresse connue, inconnue, désactivée ou limitée.
Les limites PostgreSQL sont partagées entre workers et navigateurs : cinq demandes
par adresse et trente par adresse réseau directe en quinze minutes. Les clés
sont hachées avec le secret de l’application ; les buckets expirés sont supprimés
à la demande suivante. Les en-têtes de proxy fournis par le navigateur ne sont
pas considérés comme une preuve de son adresse. Derrière un proxy, plusieurs
personnes peuvent partager cette limite : calibrer ce point avant ouverture large.

L’envoi SMTP est synchrone et ses délais peuvent varier : des réponses identiques
ne garantissent pas l’absence de toute déduction par mesure du temps. Une file
d’envoi durable pourra isoler ces délais lors de l’intégration e-mail dédiée.

Les logs applicatifs masquent `sesame`; le journal HTTP Gunicorn omet les paramètres
de requête et le référent. Vérifier séparément les journaux du proxy et du fournisseur
e-mail ; ne jamais y conserver les liens complets. Aucun lien ni boîte de réception
de test n’est exposé par les nouvelles routes publiques.

## Configuration e-mail, sans secret dans Git

Par défaut, l’envoi est désactivé et l’écran le dit explicitement. La recette peut
être relue sans compte ni accès SMTP. Les tests utilisent une boîte en mémoire.

L’activation nécessite `LOGIN_EMAIL_ENABLED=1`, une origine HTTPS fixe
`LOGIN_EMAIL_ORIGIN` dont l’hôte figure dans `DJANGO_ALLOWED_HOSTS`,
`EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`,
`DEFAULT_FROM_EMAIL` et les options TLS/SSL. L’origine fixe empêche un en-tête
Host de modifier le domaine des liens envoyés. Le transport SMTP Django peut
être raccordé à Brevo sans dépendance de l’authentification à ce fournisseur.
Les valeurs et secrets des environnements appartiennent à leur configuration
privée ; ne pas copier les accès de production vers une recette.

Les anciens essais `/employer/access/` restent isolés sur loopback et opt-in.
Ils ne sont plus la cible du bouton public. Les accès aux établissements ne
sont pas élargis : un compte ne gagne aucune appartenance en se connectant.
Les invitations, l’ouverture publique de l’espace employeur et le raccordement
Brevo restent des lots distincts.

## Vérification

`make login-test` teste l’authentification, l’expiration, l’usage unique, la CSRF,
les limites, les rôles et la session. `make test` couvre aussi les autres parcours.
Utiliser `make check`, `make format-check`, `make format-html-check`,
`make format-js-check`, `make check-js` et `make translations-check` pour les contrôles.

En recette, ouvrir les onglets publics puis le bouton de connexion, changer de
langue et vérifier le message d’inscription sur invitation et l’envoi désactivé.
L’envoi réel ne sera validé qu’après configuration privée du prestataire.
