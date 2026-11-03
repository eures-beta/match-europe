# Comptes fictifs en local et en recette

Un bandeau rouge permanent permet de choisir ou de changer de compte sans e-mail
ni mot de passe : conseiller, employeur et superadministrateur. Les trois comptes
partagés utilisent exclusivement des adresses `@demo.example.invalid`.
Toute personne visitant cet environnement peut les utiliser : aucune donnée réelle
ne doit y être saisie. Le superadministrateur conserve l’administration en lecture
seule ; le tableau conseiller permet d’essayer les invitations sans envoi réel.

## Développement local

Dans le `.env` ignoré du worktree, configurer `DJANGO_ENVIRONMENT=local`,
`TEST_ACCOUNTS_ENABLED=1` et `EMAIL_DELIVERY_ENABLED=0`, puis :

```bash
make migrate
make test-accounts-seed
make serve
```

Ouvrir `/accounts/test-accounts/`, ou suivre le bandeau. Le peuplement crée trois
comptes, un établissement fictif, une adhésion employeur et deux offres manuelles.
Il ne réinitialise ni ne supprime les essais existants. Les fixtures des offres
restent dans `employers/test_data.py`, celles des comptes dans `users`.
Aucun modèle ni migration supplémentaire n’est nécessaire.

## Protections et limites

- Désactivé par défaut ; refus de démarrage si activé hors `local`/`preview` ou
  avec envoi réel d’e-mails. Les anciens réglages de démonstration ne l’activent pas.
- Le sélecteur et le peuplement refusent une base contenant un compte dont
  l’adresse ne se termine pas par `.invalid`. Ce garde-fou ne détecte pas les
  données personnelles saisies dans le texte des offres : utiliser uniquement
  une base jetable et fictive.
- La connexion accepte uniquement les trois identités préparées, actives, avec
  rôle exact et mot de passe inutilisable. Aucune création au chargement d’une
  page, aucun identifiant arbitraire ni lien magique exposé.
- Changer de compte exige un POST protégé par CSRF et renouvelle la session.
  Les pages de sélection ne sont pas mises en cache.
- Les offres et comptes existants sont conservés aux redéploiements. Un compte
  de fixture dont les attributs ont changé provoque un refus explicite du
  peuplement, sans promotion silencieuse ni changement partiel.
- En recette, la configuration et l’appel du peuplement après les migrations
  relèvent du dépôt privé de déploiement. La production ne doit jamais l’appeler.

Vérifications PostgreSQL : `make test-accounts-test` ; suite complète : `make test`.
Les langues FR, EN et DE sont couvertes, ainsi que les refus de connexion,
la CSRF, la rotation des sessions et la préservation des essais.
