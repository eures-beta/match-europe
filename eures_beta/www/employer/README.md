# Interface employer

Import, relecture, offres et tableau de bord de l’employeur.

[Retour à la couche web](../) · [Architecture](../../../docs/ARCHITECTURE_WEB.md)

## Fichiers

- [__init__.py](__init__.py) — Déclare le paquet Python, sans modèle ni effet au chargement.
- [access.py](access.py) — Applique les protections HTTP du parcours d’import employeur.
- [dashboard.py](dashboard.py) — Prépare le tableau de bord employeur à partir de ses offres accessibles.
- [establishments.py](establishments.py) — Définit le formulaire de rattachement à un établissement.
- [forms.py](forms.py) — Définit et valide les formulaires propres aux écrans de ce parcours.
- [imports.py](imports.py) — Expose l’API des offres `/api/job-offers/`, avec extraction, relecture et enregistrement protégés.
- [pages.py](pages.py) — Rend les trois pages explicites `/employer/`, `/employer/import/` et `/employer/privacy/`, sans choisir de template depuis l’URL.
- [response_forms.py](response_forms.py) — Définit le formulaire des habitudes de réponse, avec les choix du domaine métier.
- [response_practice.py](response_practice.py) — Expose les habitudes de réponse de l’employeur via HTTP.
- [urls.py](urls.py) — Déclare les routes canoniques nommées ; les vestiges sont isolés dans public/legacy_urls.py.
- [workspace.py](workspace.py) — Présente les offres et traite les actions de leur propriétaire autorisé.

Les habitudes de réponse du profil employeur passent par `/api/employer/profile/`, sans modification du modèle.
