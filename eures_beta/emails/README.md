# Transport e-mail partagé

Les e-mails applicatifs passent par le backend Django sélectionné dans
`EMAIL_TRANSPORT`. Le transport `smtp` est le choix par défaut. Pour l’API
transactionnelle Brevo, sélectionner `brevo`, renseigner `BREVO_API_KEY` dans
les secrets d’hébergement et mettre l’adresse vérifiée de l’expéditeur dans
`DEFAULT_FROM_EMAIL`. `BREVO_FROM_NAME`, `BREVO_REPLY_TO_EMAIL` et
`BREVO_REPLY_TO_NAME` sont facultatifs.

Le transport Brevo couvre les messages texte utilisés par les liens de
connexion, les vérifications candidat et les invitations. Il génère une version
HTML échappée et reprend les en-têtes de désactivation du suivi employés par
Flask. Une réponse HTTP 201 confirme l’acceptation par Brevo. Le backend ne
relance pas automatiquement un envoi après une erreur.

Les deux transports exigent `EMAIL_DELIVERY_ENABLED=1`. Pour les liens de
connexion, activer aussi `LOGIN_EMAIL_ENABLED=1` et configurer
`LOGIN_EMAIL_ORIGIN` avec l’origine HTTPS de l’application. Vérifier que les
comptes de test instantanés sont désactivés avant d’activer l’envoi réel.

Vérifier avec `make emails-test`, puis `make test`. L’appel Brevo est simulé
dans les tests.
