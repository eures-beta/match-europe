# Templates HTML partagés

Django transforme ces fichiers en pages HTML en leur fournissant des données. `public_base.html` définit le cadre public ; `base.html` celui des espaces métier. Les pages et fragments réutilisent ces cadres et les traductions gettext. Les templates spécifiques au nouvel accueil candidat sont dans [candidates/templates](../candidates/templates/README.md). Depuis la racine, `make format-html` indente les templates et `make format-html-check` vérifie leur format.

Pour explorer ce dossier :

- [conversations/](conversations/README.md)
- [employer/](employer/README.md)
- [includes/](includes/README.md)

[Remonter au dossier parent](../README.md).
