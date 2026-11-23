# Transport et présentation e-mail partagés

`backend.py` contient le transport SMTP commun à toutes les applications.
Il utilise le backend standard Django : aucun SDK ou client spécifique à Brevo.
Le même SMTP configuré est disponible dans tous les environnements, uniquement
après activation explicite. L’envoi reste désactivé par défaut.
Les templates et parcours métier restent dans leurs applications respectives.

`rendering.py` produit l'alternative HTML commune des messages transactionnels,
à partir du même texte traduit, avec des liens explicites et du contenu échappé.
Il fournit aussi le contexte de présentation des invitations riches : confidentialité
et logos partenaires existants. Les URL des messages transactionnels utilisent
l'origine configurée et validée, sans reprendre l'en-tête Host d'une requête.
Tous les HTML partagent la carte des invitations employeur ; titre et bouton
peuvent être fournis explicitement sans déduire une action d'un texte utilisateur.
Les templates partagés vivent dans [templates/emails/](../templates/emails/).
Voir [l'inventaire, les choix et les limites de compatibilité](../../docs/EMAIL_LINKS.md).

Vérifications : `make test TESTS=tests.emails`, puis `make test`.
