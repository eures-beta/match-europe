# Lecture des documents

Extraction locale des offres pour le parcours employeur, avant relecture humaine.
Aucun modèle ni stockage propre à ce paquet.

- [document_fields.py](document_fields.py) : champs et sections, texte normalisé,
  recherches de pagination, commissions et expérience sans reprises quadratiques.
- [pdf_reader.py](pdf_reader.py) : lecture PDF/OCR dans un processus borné.
- [apps.py](apps.py) : configuration Django.
- [Tests](../../tests/documents/) : extraction, préservation des formulations et
  entrées répétitives ; `make test TESTS=tests.documents`.

La limite de 16 000 caractères ne remplace pas un algorithme prévisible. Le texte
est normalisé avant les autres regex ; conserver ce contrat et les limites de
l'en-tête. Voir le [triage CodeQL](../../docs/CODEQL_TRIAGE.md).
