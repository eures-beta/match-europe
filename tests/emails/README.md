# Tests e-mail

- `test_backend.py` : autorisation explicite et transport SMTP simulé.
- `test_rendering.py` : MIME, URL longues/signées, HTML échappé et FR/EN/DE.
- `assertions.py` : vérification des liens décodés dans les parcours métier.

`make test TESTS=tests.emails` utilise une boîte mémoire, sans envoi réel.
Voir [les choix de compatibilité](../../docs/EMAIL_LINKS.md).
