# Comptes utilisateurs

Ce paquet regroupe le compte Django unique des conseillers et employeurs. Le champ `kind` porte le rôle ; les établissements et leurs adhésions restent dans employers.

Voir [la documentation de transition](../../docs/USER_MODEL.md).

## Contenu

- [Comptes fictifs](../../docs/TEST_ACCOUNTS.md) — Sélection explicite en local/recette uniquement.
- [test_accounts.py](test_accounts.py) — Identités autorisées et garde-fous.
- [test_account_views.py](test_account_views.py) — Sélecteur et connexion POST protégée.

- [Administration en lecture seule](../../../docs/ADMIN_READONLY.md) — Modèles consultables, rôles et secrets masqués.
- [admin_base.py](admin_base.py) — Protection commune contre les écritures et affichage sûr des données structurées.

- [email_backend.py](email_backend.py) — Interdit les connexions SMTP hors production explicitement activée.

- [Invitations employeurs](../../../docs/EMPLOYER_INVITATIONS.md) — Tableau conseiller, invitation de sept jours et simulation privée des e-mails.
- [invitations.py](invitations.py) — Création explicite, jetons signés et limites.
- [invitation_views.py](invitation_views.py) — Vues conseiller et acceptation publique protégée.

- [Droits administratifs](../../../docs/ADMIN_PERMISSIONS.md) — Politique versionnée, synchronisation et création restreinte de conseillers.
- [permissions.py](permissions.py) — Matrice des droits et réconciliation des attributions.
- [admin_config.py](admin_config.py) — Retire l'édition des groupes après découverte des administrations.
- [__init__.py](__init__.py) — Identifie le paquet Python.
- [admin.py](admin.py) — Adapte l’administration Django au compte sans username et au kind immuable.
- [apps.py](apps.py) — Déclare l’application Django users.
- [forms.py](forms.py) — Valide l’adresse e-mail sans proposer d’inscription.
- [management/](management/) — Ce dossier permet à Django de découvrir les commandes du domaine utilisateurs.
- [migrations/](migrations/) — Ces migrations créent le compte commun et protègent son rôle en base. La transition depuis auth.User est préparée par la commande migrate avant de résoudre le nouveau graphe.
- [models.py](models.py) — Définit User et son gestionnaire.
- [rate_limits.py](rate_limits.py) — Limite les demandes de liens avec des compteurs partagés en base.
- [static/](static/) — Styles des écrans du compte connecté.
- [urls.py](urls.py) — Déclare les routes de connexion, confirmation et déconnexion.
- [views.py](views.py) — Envoie et vérifie les liens django-sesame pour les comptes existants.
- [tests/](tests/) — Ces tests vérifient authentification, unicité des e-mails et contraintes du rôle, y compris les mises à jour directes en base.
- [tools/](tools/) — Cet outil teste la mise à niveau dans une base locale temporaire, avec des données fictives et une suppression de la base à la fin.
- [README.md](README.md) — Présente ce dossier et son contenu.

[Remonter au dossier parent](../).

La création autonome est fermée : voir [les points d’entrée et les tests](../../docs/ACCOUNT_REGISTRATION.md).

La connexion publique utilise désormais [un lien magique](../../docs/MAGIC_LOGIN.md).
L’envoi SMTP reste désactivé jusqu’à sa configuration privée.

[Mon compte](../../docs/ACCOUNT_PAGES.md) affiche les informations de l’utilisateur
connecté en lecture seule ; le lien d’administration est réservé aux comptes staff.
