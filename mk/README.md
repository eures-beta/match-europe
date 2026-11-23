# Commandes Make par domaine

Le [Makefile racine](../Makefile) inclut explicitement ces fragments dans leur ordre
de lecture. Depuis la racine du dépôt, `make` et `make help` présentent les commandes.
Les noms, paramètres et protections des cibles restent communs à tous les environnements.

- [variables.mk](variables.mk) : variables, exports protégés et commande par défaut.
- [help.mk](help.mk) : aide qui parcourt tous les fichiers chargés par Make.
- [runtime.mk](runtime.mk) : interpréteur Python, installation et serveurs Django/Clever.
- [database.mk](database.mk) : préparation locale, migrations et permissions.
- [quality.mk](quality.mk) : Black, HTML, JavaScript, CSS et contrôles Django/documentation.
- [tests.mk](tests.mk) : suites Python/JavaScript, reprise des utilisateurs et parcours HTTPS.
- [translations.mk](translations.mk) : extraction, vérification et compilation gettext.
- [catalogues.mk](catalogues.mk) : sources ROME/ESCO, construction et audits des catalogues.
- [github.mk](github.mk) : descriptions de PR et diagnostics CI en lecture seule.
- [security.mk](security.mk) : recherche de secrets et revue des alertes de sécurité.
- [integrations.mk](integrations.mk) : évaluation explicite du service Albert.
- [matching.mk](matching.mk) : commandes locales de préparation et d'essai du matching.
- [accounts.mk](accounts.mk) : prévisualisation des e-mails de connexion et entretien des inscriptions.

Ajouter une recette au domaine concerné, puis mettre à jour cette liste et l'aide.
Garder uniquement des lignes `include mk/…mk` dans le Makefile racine ; les variables
et options vont dans `variables.mk`, l'aide dans `help.mk`. Les commandes pouvant
modifier une base ou appeler un service réel gardent leurs garde-fous et approbations.
