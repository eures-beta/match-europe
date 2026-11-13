# Couche web de Match Europe

Ce paquet contient les adaptateurs HTTP : routes, vues, formulaires d’interface et préparation des pages. Il ne contient ni modèle ni migration et n’est pas une application ajoutée à `INSTALLED_APPS`.

Les modèles, services, validations partagées et commandes restent dans les applications métier. Templates, statiques et traductions restent dans leurs dossiers communs. Les URL et les protections d’accès sont conservées.

[Paquet applicatif](../) · [Guide d’architecture](../../docs/ARCHITECTURE_WEB.md)

## Parcours

- [accounts/](accounts/) — Connexion, déconnexion, compte et orientation vers le tableau de bord du rôle connecté.
- [adviser/](adviser/) — Écrans du conseiller : suivi des rapprochements et historique ; les invitations ont leur propre paquet web.
- [candidate/](candidate/) — Accueil, questionnaire, confirmation, profil et installation PWA du candidat.
- [employer/](employer/) — Import, relecture, offres et tableau de bord de l’employeur.
- [invitations/](invitations/) — Acceptation et préparation des invitations ; les comptes et invitations restent dans leur domaine métier.
- [matching/](matching/) — Pages de rapprochement, confirmations par offre et conversations partagées.
- [occupations/](occupations/) — Adaptateur HTTP de la recherche de métiers ; le catalogue et son moteur restent dans occupations.
- [skills/](skills/) — Adaptateur HTTP des suggestions de compétences ; les références et services restent dans skills.
- [public/](public/) — Accueil et pages publiques, manifeste PWA, service worker et redirections des anciennes adresses.

## Fichiers

- [__init__.py](__init__.py) — Déclare le paquet Python commun des interfaces.
- [urls.py](urls.py) — Assemble les routes applicatives ; les endpoints techniques restent dans config.
