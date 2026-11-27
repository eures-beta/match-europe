# Planning staff autonome

Tous les comptes actifs `is_staff` peuvent consulter le planning et modifier uniquement leur propre ligne. Aucun contrôle de rôle conseiller ; les droits admin restent distincts.

Sans ligne enregistrée : présent du lundi au vendredi, absent le samedi et le dimanche. Une déclaration explicite reste prioritaire, y compris le week-end. GET ne crée aucune ligne.

- [models.py](models.py) : unique modèle `StaffDailyAvailability`, relation `user`, unicité utilisateur/jour.
- [views.py](views.py), [urls.py](urls.py) : GET/POST `/staff/planning/`, route `staff_planning`, CSRF et semaine validées.
- [admin.py](admin.py) : groupe Planning réel, consultation selon les droits existants.
- [migrations/](migrations/) : adoption du modèle déplacé par users.0012 ; users.0011 publiée reste immuable. Renommage en place, données, identifiants, séquence et permissions conservés, retour arrière testé.
- [templates/](templates/), [static/](static/) : interface et CSS locaux, layout commun et gettext FR/EN/DE.
- [tests/](tests/) : droits, propriété, défauts, déclarations explicites et aller-retour PostgreSQL.
- [preview_data.py](preview_data.py) : exemple fictif appelé par le préparateur commun, sans écraser les essais.

Seules intégrations : compte `AUTH_USER_MODEL`, layout/middleware de langue, liens du header et de l’espace conseiller. Les vues et données ne dépendent pas de `www` ; cette exception architecturale prépare une extraction ultérieure.

Tests : `make test TESTS=eures_beta.planning.tests` ; l’entrée `make test` les découvre aussi.
