# Interface employeur : CSS et JavaScript

Ces fichiers animent les pages employeur : lecture et relecture d’une offre, étapes du formulaire, métiers, langues et contact. `offer-import-api.js` porte les échanges avec l’API d’import ; le serveur garde la responsabilité des permissions et validations. Depuis la racine, `make format-js` applique le format JavaScript et `make format-js-check` le vérifie.

## Contenu de ce dossier

### Dossiers

- [assets/](assets/) — Ce dossier conserve les images et logos utilisés par les pages, dont les marques des partenaires et Match Europe.

### Fichiers

- [alternative.css](alternative.css) — Feuille de styles pour présentation de la variante d’interface employeur.
- [condition-fields.js](condition-fields.js) — JavaScript pour champs guidés des conditions de travail.
- [contact.js](contact.js) — JavaScript pour formulaire de contact employeur.
- [import.js](import.js) — JavaScript pour parcours d’import de l’offre.
- [language-fields.js](language-fields.js) — JavaScript pour choix des langues et niveaux requis.
- [occupation-picker.css](occupation-picker.css) — Feuille de styles pour sélecteur de métiers ESCO/ROME.
- [occupation-picker.js](occupation-picker.js) — JavaScript pour sélecteur de métiers ESCO/ROME.
- [offer-import-api.js](offer-import-api.js) — JavaScript pour échanges du navigateur avec l’API d’import d’offres.
- [push-test.js](push-test.js) — JavaScript pour interface de diagnostic Push.
- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.
- [review-steps.css](review-steps.css) — Feuille de styles pour navigation et présentation des étapes de relecture.
- [review-steps.js](review-steps.js) — JavaScript pour navigation et présentation des étapes de relecture.
- [review.js](review.js) — JavaScript pour relecture et correction des informations de l’offre.
- [site.css](site.css) — Feuille de styles pour styles communs des pages employeur.

[Remonter au dossier parent](../).
