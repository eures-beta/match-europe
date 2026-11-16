# Ressources statiques communes

CSS, JavaScript et images servis par Django. Les ressources propres à une
application peuvent aussi vivre dans son dossier `static/`. Le nom utilisé par
`{% static %}` reste indépendant de cet emplacement physique.

[Retour au projet Django](../) · [Séparation HTML/CSS](../../docs/HTML_CSS.md)

## Dossiers

- [admin/](admin/) — Contrôles de navigation et de filtres de l'administration.
- [adviser/](adviser/) — Styles propres aux écrans des conseillers.
- [design-system/](design-system/) — Tokens, thème Bootstrap, démonstrations et polices.
- [employer/](employer/) — Styles et interactions du parcours employeur.
- [public/](public/) — Mise en page et actions d'en-tête partagées.
- [pwa/](pwa/) — Icônes et scripts d'installation et d'abonnement de la PWA.
- [vendor/](vendor/) — Ressources tierces conservées sans reformatage.

## Fichiers

- [data-protection.css](data-protection.css) — Présentation de la notice de protection des données.
- [eures-logo.jpg](eures-logo.jpg) — Image du logo EURES utilisée par les pages.
- [home.css](home.css) — Présentation de l'accueil public.
- [icon.svg](icon.svg) — Icône vectorielle du site.
- [journal.css](journal.css) — Présentation du journal du projet.
- [login.css](login.css) — Présentation du formulaire de connexion.
- [public-brand.css](public-brand.css) — Harmonisation commune de la marque sur les pages publiques.
- [sw.js](sw.js) — Notifications Push et ouverture contrôlée des conversations, sans cache de pages privées.
