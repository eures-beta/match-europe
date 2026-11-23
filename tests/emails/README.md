# Tests e-mail

- `test_backend.py` : autorisation explicite et transport SMTP simulé.
- `test_rendering.py` : MIME, URL longues/signées, HTML échappé, FR/EN/DE,
  carte partagée, logos et origine du pied de page contrôlée.
- `assertions.py` : vérification des liens décodés dans les parcours métier.

`make test TESTS=tests.emails` utilise une boîte mémoire, sans envoi réel.
Voir [les choix de compatibilité](../../docs/EMAIL_LINKS.md).
