# Historique du schéma employeur

Ces migrations appartiennent au [domaine employeur](../). Django suit leurs
dépendances, pas seulement leur numéro ; les fichiers publiés restent immuables.

- [__init__.py](__init__.py) — Déclare le paquet des migrations.
- [0001_autonomous_schema.py](0001_autonomous_schema.py) — Installe le schéma autonome du domaine.
- [0002_unify_users.py](0002_unify_users.py) — Rattache les données aux comptes utilisateurs communs.
- [0003_rename_employer_models.py](0003_rename_employer_models.py) — Clarifie les noms des modèles employeur.
- [0004_employerresponsepractice.py](0004_employerresponsepractice.py) — Ajoute les habitudes de réponse.
- [0005_employer_profile.py](0005_employer_profile.py) — Adopte le profil employeur.
- [0006_joboffer_structured_requirements.py](0006_joboffer_structured_requirements.py) — Structure les conditions des offres.
- [0007_remove_retired_employer_models.py](0007_remove_retired_employer_models.py) — Retire les anciens modèles abandonnés.
- [0008_harmonize_model_names.py](0008_harmonize_model_names.py) — Harmonise les noms du schéma PostgreSQL.
- [0009_joboffer_employer_contact_and_more.py](0009_joboffer_employer_contact_and_more.py) — Introduit les premiers champs du dépôt conseiller, conservés comme historique.
- [0010_remove_joboffer_email_and_more.py](0010_remove_joboffer_email_and_more.py) — Centralise l’email dans le compte propriétaire et vérifie les rôles.
- [0011_prepare_company_cleanup.py](0011_prepare_company_cleanup.py) — Ordonne les deux branches avant le retrait des établissements.
- [0009_remove_company_workspaces.py](0009_remove_company_workspaces.py) — Supprime établissements, adhésions et rattachement après ces prérequis.

Voir le [contrat de propriété et de migration](../../../docs/EMPLOYER_OFFER_OWNERSHIP.md)
pour les données conservées et la préparation des bases ayant appliqué l’ancienne
branche isolée.
