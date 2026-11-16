# Match Europe — vue d'ensemble

Les conseillers actifs consultent toutes les offres employeur enregistrées et
leur détail en lecture seule ; cela ne modifie pas l’éligibilité au matching.
Voir [le contrat de consultation](ADVISER_EMPLOYER_OFFERS.md).

Match Europe facilite le recrutement et la mobilité professionnelle entre pays
européens, avec l'appui des conseillers EURES. Le projet Django/PostgreSQL/Bootstrap
est distinct de l'ancien prototype Flask/Grist ; une expérimentation historique
ne constitue pas une restriction permanente du produit.

## Rôles et parcours

- **Candidat** : décrire progressivement son projet et ses compétences, vérifier
  son adresse, retrouver son profil, examiner une offre et choisir ce qui peut être
  transmis. Une revue par offre précède, selon le parcours, une conversation à trois.
- **Employeur** : compte invité, lecture d'une offre par URL/PDF/texte,
  relecture guidée, sauvegarde et suivi de ses offres. Les droits restent liés
  au compte propriétaire, pas à une session de démonstration.
- **Conseiller** : inviter, examiner les rapprochements et leurs explications,
  décider et accompagner les échanges. Tous les conseillers actifs ont les mêmes
  droits métier ; les consentements candidat restent distincts.
- **Administration** : consultation autorisée des modèles, avec secrets masqués
  et sans écriture, y compris pour les superutilisateurs.
- **Équipe technique** : tests et données fictives explicites ; déploiement et
  configuration des services dans les dépôts privés.

## Organisation du code

- `users` porte les comptes, rôles et connexion ; `invitations` les invitations.
- `candidates` porte questionnaire, profil, consentements du parcours et abonnement Push.
- `employers` porte offres, établissements et profil employeur.
- `occupations` porte la recherche métiers ESCO/ROME ; `skills` les compétences
  et suggestions appuyées sur les sources officielles.
- `matching` porte rapprochements, évaluations, décisions, revues d'offres et conversations.
- `documents`, `emails`, `integrations` et `observability` portent les services
  de support ; toutes ces responsabilités ne sont pas de nouvelles applications installées.
- `www/` regroupe routes, vues et formulaires par parcours sans porter les modèles.
- `templates/`, ressources statiques et catalogues gettext gardent leurs emplacements
  documentés ; les tests automatisés sont dans `tests/` à la racine.

Les noms des modèles, relations et objets PostgreSQL suivent une
[convention commune vérifiée](MODEL_NAMING.md), avec migrations préservant les données.

Voir [l'architecture web](ARCHITECTURE_WEB.md), [les décisions](DECISIONS.md)
et les README des paquets pour le détail des responsabilités.

## Contrats communs

Les mêmes fonctionnalités métier sont disponibles en local, recette et production.
Les rôles, la propriété, CSRF, les consentements et l'authentification restent
vérifiés ; la configuration manquante d'un service ne devient pas une simulation.
`ALBERT_SIMULATED` est explicite ; `EMAIL_DELIVERY_ENABLED` exige le transport.
Les comptes de démonstration, sous `DEMO_ACCOUNTS_ENABLED`, sont un outil distinct
réservé aux bases fictives local/recette avec e-mails réels désactivés.

Les interfaces utilisent gettext FR/EN/DE, Bootstrap/ECL et les règles EURES/ELA ;
les durées, limites et consentements annoncés doivent refléter les capacités réelles.
Une fusion, un résultat de tests ou une ancienne note ne prouve pas un déploiement.

## Où continuer

- [Reprise actuelle](../HANDOFF.md) : points ouverts et PR de référence.
- [Décisions](DECISIONS.md) : contrats validés et justification.
- [Développement](DEVELOPPEMENT.md) et [tests](TESTS.md) : commandes Make et préparation.
- [Parité](ENVIRONMENT_PARITY.md) : services configurés et différence avec les outils fictifs.
- [Retours aux agents](AGENT_FEEDBACK.md) : exemples de régressions à éviter.
- [Politique documentaire](DOCUMENTATION.md) : budgets et entretien.

L'histoire des anciens parcours, écrans prototypes et validations reste dans
[l'historique Git](https://github.com/eures-beta/match-europe/commits/main/docs/VUE_ENSEMBLE.md)
et les PR, plutôt que dans une seconde chronologie à maintenir ici.
