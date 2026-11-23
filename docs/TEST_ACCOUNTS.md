# Comptes de démonstration en local et en environnement jetable

Le bandeau permanent annonce les données fictives et interdit la saisie de données
personnelles réelles. Son lien ouvre cinq boutons, dans cet ordre : **Conseiller**,
**Employeur**, **Candidat (profil complet)**, **Candidat (profil incomplet)**,
**Super administrateur**. Les textes sont traduits en français, anglais et allemand.
Les comptes sont partagés entre toutes les personnes testant cet environnement ;
toutes les modifications sont définitivement perdues à la fin de son cycle de vie.
Le superadministrateur conserve une administration Django en consultation uniquement.

## Jeu de données et préparation

Les deux candidats visibles montrent un profil complet compatible et un profil
comportant des informations à préciser, avec une revue déjà répondue. Trois autres
candidats restent dans les données, sans bouton de connexion : disponibilité trop
tardive, horaires incompatibles et permis absent. Ils illustrent les différences
de matching dans les listes du conseiller. Le sélecteur est donc un sous-ensemble
des comptes fictifs préparés, pas une liste de tous les utilisateurs.

Un seul employeur possède les offres manuelles et l'offre d'entretien structurée,
avec ses compétences et exigences. Sur une base neuve, huit comptes sont créés :
deux conseillers (dont le superadministrateur), un employeur et cinq candidats.
Les identifiants des candidats et les états de leurs parcours ne sont pas fusionnés.

Dans le `.env` ignoré du worktree : `DJANGO_ENVIRONMENT=local`,
`DEMO_ACCOUNTS_ENABLED=1`, `EMAIL_DELIVERY_ENABLED=0`. Puis :

```bash
make migrate
make test-accounts-seed
make run
```

Ouvrir `/accounts/test-accounts/` ou suivre le bandeau. Le même jeu est préparé en
local et en environnement jetable, sans variante réservée aux notifications Push.
Les fixtures des offres sont dans `employers/test_data.py`, celles des comptes
dans `users`, les cas de matching dans `matching/management/commands/seed_matching_trial.py`.
Le dépôt privé configure les environnements jetables et lance leur peuplement.

Le jeu complet ajoute treize offres et les états de revue, conversations et
accompagnements détaillés dans [l'inventaire des données](PREVIEW_DATASET.md).
`make test-accounts-seed SEED_ARGS=--report` produit leurs compteurs sans écrire ;
`SEED_ARGS=--minimal` réserve le petit jeu aux tests automatisés ciblés.

## Conservation des essais des anciennes démonstrations

Le peuplement réunit les offres de `employer@matching-trial.invalid` sous le compte
`employer@demo.example.invalid`, ainsi que leur accès aux conversations. Il conserve
les UUID, contenus, compétences, exigences, révisions, dates, messages, réponses,
décisions et consentements ; aucun effacement ou réinitialisation des essais.

Un profil employeur personnel est transféré si le compte de destination n'en a pas.
Si les deux comptes en ont un, aucun n'est écrasé : celui de l'ancien compte reste
consultable dans l'administration. Les noms déjà renseignés ne sont pas remplacés.
Les invitations acceptées et auteurs historiques restent associés à leur identité
d'origine. L'ancien compte est désactivé, retiré du sélecteur et conservé pour ces
preuves ; il n'est pas recréé dans une base neuve. Aucune migration de schéma ni
modification de production n'est nécessaire pour cette consolidation.

## Protections et vérification

- Désactivé par défaut, réservé à `local`/`preview`, avec envois réels désactivés.
  Une configuration incompatible provoque un refus explicite.
- Sélecteur, peuplement et consolidation refusent une base contenant un compte
  dont l'adresse ne se termine pas par `.invalid`. Ce contrôle ne détecte pas des
  données personnelles saisies dans un texte : utiliser uniquement une base fictive.
- Connexion limitée aux cinq identités préparées, actives, avec rôle exact et mot
  de passe inutilisable ; aucune création implicite à l'ouverture d'une page.
- Changer de compte exige un POST protégé par CSRF, renouvelle la session et ne
  permet pas une destination arbitraire. Les pages ne sont pas mises en cache.
- Un compte réservé dont les attributs ont changé bloque le peuplement, sans
  promotion silencieuse ni changement partiel. Répéter la commande conserve les essais.

Tests ciblés : `make test TESTS='tests.users.test_test_accounts tests.users.test_demo_employers'`.
Ils vérifient ordre/libellés FR/EN/DE, accès interdits, données anciennes non vides,
empreintes de consentement, conservation des auteurs et répétition sans perte.
