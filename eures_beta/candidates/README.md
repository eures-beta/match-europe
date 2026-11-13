# Domaine candidat

Profils, validation des réponses, inscription vérifiée et brouillons. L’interface HTTP utilise ces règles depuis [www/candidate/](../www/candidate/).

[Paquet applicatif](../) · [Architecture web](../../docs/ARCHITECTURE_WEB.md)

## Dossiers

- [management/](management/) — Commandes du domaine, indépendantes des pages web.
- [migrations/](migrations/) — Historique Django du schéma, conservé lors du déplacement des interfaces.
- [static/](static/) — Ressources du navigateur conservées à leur emplacement actuel.
- [templates/](templates/) — Templates du domaine conservés à leur emplacement actuel.

## Fichiers

- [__init__.py](__init__.py) — Déclare le paquet métier.
- [admin.py](admin.py) — Enregistre les modèles dans l’administration en consultation.
- [apps.py](apps.py) — Configure l’application Django et son identité stable.
- [behaviour_help.py](behaviour_help.py) — Décrit les savoir-être et leurs aides traduisibles.
- [forms.py](forms.py) — Valide le questionnaire partagé par le modèle, les services et les pages.
- [language_choices.py](language_choices.py) — Définit les langues et la validation de leurs niveaux.
- [models.py](models.py) — Définit les données persistantes, leurs relations et contraintes.
- [occupation_choices.py](occupation_choices.py) — Résout les métiers et références du questionnaire.
- [pending.py](pending.py) — Gère les brouillons et demandes de confirmation temporaires.
- [preview_push.py](preview_push.py) — Gère les clés et envois Push de recette ; l’abonnement HTTP est dans www.
- [registration.py](registration.py) — Vérifie l’inscription et conserve le profil après confirmation.
- [schedule_rules.py](schedule_rules.py) — Valide la cohérence des horaires et conditions déclarées.
- [skill_choices.py](skill_choices.py) — Définit les choix de compétences du profil candidat.
