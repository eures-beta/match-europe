# Domaine candidat

Profils, suggestions de vérification des préférences, validation des réponses, inscription vérifiée et brouillons. L’interface HTTP utilise ces règles depuis [www/candidate/](../www/candidate/).

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
- Le contact d’équipe des retours candidat vient du [contexte web commun](../www/contact.py).
- [forms.py](forms.py) — Valide le questionnaire partagé par le modèle, les services et les pages.
- [language_choices.py](language_choices.py) — Définit les langues et la validation de leurs niveaux.
- [models.py](models.py) — Définit le profil, les abonnements Push et CandidateProfileReviewSuggestion ; la détection des refus répétés reste dans matching.
  Le compte candidat du profil est immuable, avec contrôle modèle et PostgreSQL ; voir [les invariants d'auteur](../../docs/MATCHING_AUTHORS.md).
- [occupation_choices.py](occupation_choices.py) — Résout les métiers et références du questionnaire.
- [pending.py](pending.py) — Gère les brouillons et demandes de confirmation temporaires.
- [push.py](push.py) — Gère les clés et envois Push candidats ; l’abonnement HTTP est dans www. Voir [la rotation et le renouvellement des abonnements](../../docs/CANDIDATE_PUSH.md).
- [registration.py](registration.py) — Vérifie l’inscription, conserve le profil confirmé et déclenche son matching après commit.
- [schedule_rules.py](schedule_rules.py) — Valide la cohérence des horaires et conditions déclarées.
- [skill_choices.py](skill_choices.py) — Définit les choix de compétences du profil candidat.
