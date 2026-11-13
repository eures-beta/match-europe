# Invitations

Application Django dédiée aux invitations d'employeurs, de candidats et de
conseillers. `users` conserve les comptes, l'authentification et la synchronisation
commune des droits ; cette application possède le parcours d'invitation.

- `models.py`, `defaults.py` : invitation, destinataire, dates et expiration ;
- `services.py` : création, signature des liens, validation et quota ;
- `adviser.py` : préparation manuelle/CSV, aperçu, envoi, suivi et relances ;
- `views.py`, `forms.py`, `urls.py` : invitation simple et acceptation protégée ;
- `permissions.py`, `signals.py`, `eligibility.py` : rôle conseiller actif,
  droits historiques et reconnaissance des candidats invités ;
- `templates/invitations/`, `static/invitations/` : pages, e-mails et styles ;
- `admin.py` : consultation des métadonnées, sans modification ni jeton exposé ;
- `management/commands/invitation_email.py` : simulation privée, sans envoi ;
- `tests/` : parcours, rôles, liens, traductions et migrations sur données non vides.

## Déplacement du modèle existant

`invitations.0001` reprend l'état du modèle existant ; `users.0009` retire cet
état de `users`. Les deux utilisent `SeparateDatabaseAndState` : aucune création
ou suppression de table, aucune copie de lignes. Le nom physique
`users_invitation` et sa contrainte d'unicité sont conservés volontairement.
Une installation neuve crée la table par les migrations historiques avant ce
transfert. Les anciennes migrations restent inchangées.

`invitations.0002` termine la chaîne après `users.0009`, sans opération SQL.
Ainsi, une migration ciblant l'application invitations termine aussi le transfert
avant la création automatique des permissions par Django.

Le ContentType passe de `users.invitation` à `invitations.invitation` en gardant
son identifiant : permissions, attributions et journal d'administration restent
rattachés. Un conflit de ContentTypes bloque la migration au lieu de fusionner
des droits. Le retour arrière effectue le transfert inverse.

Les URL publiques, le sel de signature et la clé de session restent identiques :
les invitations déjà envoyées restent utilisables. Le seul import conservé dans
`users.models` sert à résoudre le callable référencé par `users.0004`.

Appliquer l'ensemble avec `make migrate`, puis `make check` et `make test`.
Voir [le parcours et les limites](../../docs/INVITATIONS.md).
