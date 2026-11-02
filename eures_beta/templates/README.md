# Templates HTML partagés

Django transforme ces templates en pages HTML. `public_base.html` porte le cadre public ; les pages accueil, projet, journal, employeur et les annonces en construction le réutilisent. Les textes sont traduits avec gettext. L’accueil candidat possède ses templates dans son application.

## Contenu de ce dossier

### Dossiers

- [employer/](employer/) — `landing.html`, `import.html`, `import-v2.html` et `privacy.html` portent les pages du parcours employeur.
- [includes/](includes/) — Ces petits templates sont inclus dans d’autres pages.

### Fichiers

- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [employer_attachment.html](employer_attachment.html) — Template Django pour pièces jointes employeur.
- [employer_auth_shell.html](employer_auth_shell.html) — Template Django pour cadre commun des écrans de connexion employeur.
- [employer_login.html](employer_login.html) — Template Django pour connexion employeur.
- [employer_workspace.html](employer_workspace.html) — Template Django pour espace de travail employeur.
- [home.html](home.html) — Template Django pour page d’accueil.
- [journal.html](journal.html) — Template Django pour le journal du projet.
- [project.html](project.html) — Template Django pour la présentation du projet.
- [public_base.html](public_base.html) — Template Django pour cadre commun des pages publiques.
- [under_construction.html](under_construction.html) — Template Django pour page signalant une fonctionnalité en construction.

[Remonter au dossier parent](../).
