# Transport e-mail partagé

`backend.py` contient le transport SMTP commun à toutes les applications.
Il utilise le backend standard Django : aucun SDK ou client spécifique à Brevo.
Le même SMTP configuré est disponible dans tous les environnements, uniquement
après activation explicite. L’envoi reste désactivé par défaut.
Les templates et parcours métier restent dans leurs applications respectives.

`rendering.py` produit l'alternative HTML commune des messages transactionnels,
à partir du même texte traduit, avec des liens explicites et du contenu échappé.
Les templates partagés vivent dans [templates/emails/](../templates/emails/).
Voir [l'inventaire, les choix et les limites de compatibilité](../../docs/EMAIL_LINKS.md).

Vérifications : `make test TESTS=tests.emails`, puis `make test`.
