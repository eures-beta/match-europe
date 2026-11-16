# Tests des documents

- [test_document_reader.py](test_document_reader.py) : extraction FR/EN/DE,
  sections, OCR, imports et conservation des formulations.
- [test_extraction_safety.py](test_extraction_safety.py) : pagination, commissions,
  expérience, répétitions hostiles et protections de normalisation/en-tête.

Exécuter `make test TESTS=tests.documents`. Les données sont fictives ; aucun OCR,
SMTP ou service distant réel dans ces tests. [Service](../../eures_beta/documents/).
