# Anciennes migrations journeys

Ces migrations retracent la création des objets historiques, puis le transfert de leur état vers les nouvelles applications. Elles permettent de faire évoluer une base existante sans recréer ses données. Les noms de tables `journeys_*` peuvent donc rester légitimes. Les modifications demandent de vérifier une migration depuis une base existante, pas seulement la création d’une base vide.

## Contenu de ce dossier

### Fichiers

- [0001_initial.py](0001_initial.py) — Établit l’état initial de migration de cette application.
- [0002_employerimport.py](0002_employerimport.py) — Conserve l’étape historique « employerimport » dans la chaîne de migration journeys.
- [0003_employerimport_initial_sent_at.py](0003_employerimport_initial_sent_at.py) — Conserve l’étape historique « employerimport_initial_sent_at » dans la chaîne de migration journeys.
- [0004_employer_contact_and_adviser.py](0004_employer_contact_and_adviser.py) — Conserve l’étape historique « employer_contact_and_adviser » dans la chaîne de migration journeys.
- [0005_employer_email_link.py](0005_employer_email_link.py) — Conserve l’étape historique « employer_email_link » dans la chaîne de migration journeys.
- [0006_employercompany_employeridentity_and_more.py](0006_employercompany_employeridentity_and_more.py) — Conserve l’étape historique « employercompany_employeridentity_and_more » dans la chaîne de migration journeys.
- [0007_employer_offer_workspace.py](0007_employer_offer_workspace.py) — Conserve l’étape historique « employer_offer_workspace » dans la chaîne de migration journeys.
- [0008_employer_search_simulation.py](0008_employer_search_simulation.py) — Conserve l’étape historique « employer_search_simulation » dans la chaîne de migration journeys.
- [0009_move_conversations.py](0009_move_conversations.py) — Conserve l’étape historique « move_conversations » dans la chaîne de migration journeys.
- [0010_delete_notification.py](0010_delete_notification.py) — Conserve l’étape historique « delete_notification » dans la chaîne de migration journeys.
- [0011_alter_candidate_document_alter_offer_document_and_more.py](0011_alter_candidate_document_alter_offer_document_and_more.py) — Conserve l’étape historique « alter_candidate_document_alter_offer_document_and_more » dans la chaîne de migration journeys.
- [0012_alter_match_candidate_delete_candidate.py](0012_alter_match_candidate_delete_candidate.py) — Conserve l’étape historique « alter_match_candidate_delete_candidate » dans la chaîne de migration journeys.
- [0013_remove_offer_adviser_remove_offer_document_and_more.py](0013_remove_offer_adviser_remove_offer_document_and_more.py) — Conserve l’étape historique « remove_offer_adviser_remove_offer_document_and_more » dans la chaîne de migration journeys.
- [0014_alter_match_offer_alter_answer_question_delete_offer_and_more.py](0014_alter_match_offer_alter_answer_question_delete_offer_and_more.py) — Conserve l’étape historique « alter_match_offer_alter_answer_question_delete_offer_and_more » dans la chaîne de migration journeys.
- [0015_remove_event_actor_remove_profile_adviser_and_more.py](0015_remove_event_actor_remove_profile_adviser_and_more.py) — Conserve l’étape historique « remove_event_actor_remove_profile_adviser_and_more » dans la chaîne de migration journeys.
- [0016_remove_employerimport_company_and_more.py](0016_remove_employerimport_company_and_more.py) — Conserve l’étape historique « remove_employerimport_company_and_more » dans la chaîne de migration journeys.
- [0017_remove_answer_unique_answer_and_more.py](0017_remove_answer_unique_answer_and_more.py) — Conserve l’étape historique « remove_answer_unique_answer_and_more » dans la chaîne de migration journeys.
- [0018_delete_match.py](0018_delete_match.py) — Conserve l’étape historique « delete_match » dans la chaîne de migration journeys.
- [__init__.py](__init__.py) — Identifie ce dossier comme un paquet Python.
- [README.md](README.md) — Présente ce dossier et guide la lecture de son contenu.

[Remonter au dossier parent](../).
