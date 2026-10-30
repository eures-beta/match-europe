# Templates HTML partagés

Django transforme ces fichiers en pages HTML en leur fournissant des données. `public_base.html` définit le cadre public ; `base.html` celui des espaces métier. Les pages et fragments réutilisent ces cadres et les traductions gettext. Les templates spécifiques au nouvel accueil candidat sont dans [candidates/templates](../candidates/templates/). Depuis la racine, `make format-html` indente les templates et `make format-html-check` vérifie leur format.

## Contenu de ce dossier

### Dossiers

- [conversations/](conversations/) — `detail.html` affiche une conversation et ses messages avec le cadre HTML partagé.
- [employer/](employer/) — `landing.html`, `import.html`, `import-v2.html` et `privacy.html` portent les pages du parcours employeur.
- [includes/](includes/) — Ces petits templates sont inclus dans d’autres pages.

### Fichiers

- [access.html](access.html) — Template Django pour accès utilisateurs.
- [base.html](base.html) — Template Django pour cadre commun des espaces métier.
- [candidate.html](candidate.html) — Template Django pour fiche candidat du parcours métier.
- [confirm.html](confirm.html) — Template Django pour confirmation du parcours.
- [dashboard.html](dashboard.html) — Template Django pour tableau de suivi des rapprochements.
- [employer_attachment.html](employer_attachment.html) — Template Django pour pièces jointes employeur.
- [employer_auth_shell.html](employer_auth_shell.html) — Template Django pour cadre commun des écrans de connexion employeur.
- [employer_login.html](employer_login.html) — Template Django pour connexion employeur.
- [employer_workspace.html](employer_workspace.html) — Template Django pour espace de travail employeur.
- [home.html](home.html) — Template Django pour page d’accueil.
- [imported_offer.html](imported_offer.html) — Template Django pour offre importée.
- [match.html](match.html) — Template Django pour rapprochement candidat-offre.
- [offer.html](offer.html) — Template Django pour fiche offre.
- [public_base.html](public_base.html) — Template Django pour cadre commun des pages publiques.
- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [under_construction.html](under_construction.html) — Template Django pour page signalant une fonctionnalité en construction.
- [upload.html](upload.html) — Template Django pour téléversement de document.

[Remonter au dossier parent](../).
