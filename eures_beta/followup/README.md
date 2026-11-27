# Domaine followup

Accompagnement des candidats et des offres, prochaines actions, relances et issue du recrutement. Ce domaine consulte les rapprochements et mises en relation sans modifier leurs accords.

[Paquet applicatif](../) · [Découpage des domaines](../../docs/MATCHING_DOMAINS.md)

## Dossiers

- [migrations/](migrations/) — Historique versionné du schéma ; les migrations déplacent les tables en conservant les données.
- [templates/](templates/) — Templates Django de présentation de ce domaine.

## Fichiers

- [__init__.py](__init__.py) — Déclare le paquet Python.
- [admin.py](admin.py) — Expose les métadonnées dans l’administration Django en consultation uniquement.
- [apps.py](apps.py) — Déclare l’application et son libellé traduit dans l’administration.
- [match_followup.py](match_followup.py) — Gère les prochaines actions et relances sur une mise en relation.
- [match_lifecycle.py](match_lifecycle.py) — Présente l’avancement du matching et enregistre son issue vérifiée.
- [models.py](models.py) — Définit les modèles persistants de ce domaine et leurs contraintes.
- [search_queue.py](search_queue.py) — Identifie les candidats et offres qui nécessitent une recherche externe.
