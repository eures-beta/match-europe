# Consignes de développement

## Commandes locales réutilisables pour les agents

- Utiliser les cibles existantes directement : `make test` pour la suite complète,
  `make employer-test` pour les modules de tests du parcours employeur, `make check`
  pour Django et les migrations. Le filtre employeur ne remplace pas la suite
  complète pour valider les interactions entre domaines.
- Chaque worktree possède son propre `.venv`, installé avec `make install-test`,
  et son `.env` ignoré par Git. Ne pas utiliser le Python d’un autre worktree ou
  d’une ancienne PR. Installer les dépendances avant de lancer les tests.
- Configurer une valeur `PGDATABASE` distincte par worktree dans `.env`, avec un
  rôle PostgreSQL de développement autorisé à créer la base de test. Django
  utilise normalement `test_<PGDATABASE>`. Ne pas partager cette base entre
  exécutions concurrentes ; ne jamais utiliser des identifiants de production.
- Pour les vérifications usuelles, lancer les commandes sans paramètres, sans
  wrapper `bash -lc`, sans `cd` incorporé et sans redirection shell `> … 2>&1`.
  Utiliser le répertoire de travail de l’outil et récupérer directement sa sortie.
  Cela permet la reconnaissance des préfixes d’approbation ciblés lorsque le
  client les a autorisés. Les options de diagnostic restent possibles au besoin.
- Ne pas masquer une opération supplémentaire dans une cible Makefile pour
  contourner une approbation. Ces consignes ne constituent pas une règle
  d’autorisation : les droits et règles locales du client continuent de s’appliquer.
- Lors d’une reprise sur une branche ancienne, relire les consignes de la branche
  de travail et les changements de consignes de `main` avant de poursuivre.

## Pull requests et collaboration en équipe

### Création

- Créer une branche dédiée au travail demandé, avec le préfixe `codex/` sauf
  instruction contraire. La destination habituelle est `main`.
- L'agent peut choisir un titre court et descriptif sans demander de confirmation.
  Respecter un titre fourni par l'humain ; celui-ci peut aussi le modifier ensuite.
- L'agent peut rédiger automatiquement la description : problème, changement
  apporté, vérifications et limites utiles à la relecture.
- Assigner la PR au compte GitHub de l'humain qui demande le travail. Vérifier
  son identifiant ; s'il est inconnu ou ambigu, le demander sans l'inventer.
  L'agent agit comme assistant de cet humain.
- Demander la relecture au compte GitHub `dejafait` par défaut, sauf consigne
  explicite différente. Si GitHub empêche cette demande ou l'assignation,
  signaler la limite sans prétendre que l'opération a réussi.
- Les PR empilées sont permises : une branche B peut cibler la branche A d'une
  PR encore ouverte, plutôt que `main`. Vérifier le contexte et demander la
  branche de base lorsque ce choix est ambigu ; ne pas poser systématiquement
  la question si la destination est déjà claire.

### Pendant la relecture

- Ne pas rebaser automatiquement les PR sur les nouveaux commits de leur
  branche de destination pendant leur vie courante. Le faire sur demande ou
  dans la préparation de la fusion décrite ci-dessous.
- Communiquer à l'humain les commentaires des reviewers, en expliquer les
  conséquences et proposer les suites à donner. Distinguer les corrections
  nécessaires des suggestions et des points de désaccord.

### Fusion et nettoyage

- Une demande de création ou de relecture de PR n'autorise pas sa fusion.
- Lorsqu'une fusion est autorisée, actualiser la branche de destination et
  rebaser la branche de travail sur ses derniers commits avant la fusion.
  Résoudre les conflits, revoir le diff et refaire les vérifications pertinentes.
- Ne jamais créer de merge commit. Ne pas squasher les commits sauf demande
  explicite de l'humain. Utiliser une fusion conservant un historique linéaire
  sans squash ; si les réglages GitHub l'empêchent, signaler le blocage sans
  contourner les règles du dépôt.
- Si le rebase impose de réécrire une branche déjà publiée, utiliser uniquement
  `--force-with-lease`, après vérification de l'état distant.
- Après la fusion d'une PR A, retargeter les PR empilées qui ciblaient sa branche
  vers sa destination effective (généralement `main`). Vérifier leur diff pour
  éviter de représenter les changements déjà intégrés. Si nécessaire, adapter
  uniquement les branches dépendantes concernées pour préserver leur travail.
- Supprimer la branche distante fusionnée lorsqu'elle ne sert plus de base à
  une PR ouverte. Ne pas supprimer une branche encore nécessaire.
- Ne pas rebaser ni modifier automatiquement les autres PR ou branches
  indépendantes après une fusion : cela crée du bruit et des notifications
  inutiles. Le traitement des PR empilées directement dépendantes est la seule
  exception à ce nettoyage ciblé, sauf demande explicite de l'humain.

## Séparation entre code et exploitation

Ce dépôt public contient le code et les instructions de développement local.
Les destinations, configurations et procédures propres aux environnements
restent dans les dépôts privés de déploiement. Ne pas inscrire ici de secrets,
d’accès serveur ou de consigne imposant une infrastructure particulière.

## Descriptions des pull requests

Avant de créer ou de modifier une description de PR, lire le modèle commun :
https://github.com/eures-beta/.github/blob/main/pull_request_template.md

Cette lecture est obligatoire, y compris avec la CLI ou l’API GitHub : le modèle
hérité n’est pas présent dans le clone local. Rédiger en français, conserver les
rubriques pertinentes et remplacer les textes d’aide par le pourquoi, le comment
et les instructions de test propres à la PR. Les sections indiquées comme
optionnelles peuvent être omises si elles ne s’appliquent pas.

Distinguer les tests exécutés de ceux restant à faire ; ne cocher que les
vérifications réalisées. Si le modèle est inaccessible, le signaler et utiliser
les rubriques Pourquoi, Comment, À vérifier et Comment tester, sans inventer
son contenu. Ne pas recopier le modèle dans ce dépôt : GitHub utilise le modèle
commun en l’absence de modèle local.
---

# AGENTS.md

This file defines the permanent working rules for the Match Europe project.

It applies to both human developers and AI agents working in the repository.

Rules are classified into three levels:

- **MUST**: mandatory and non-negotiable without explicit approval.
- **SHOULD**: architecture or quality rule to follow unless there is a clear justification.
- **CONVENTION**: shared working rule intended to maintain consistency across the project.

---

## Shared project references — read at the start of a task

Before working on any EURES beta / Match Europe area, read:

1. `docs/VUE_ENSEMBLE.md` — overall purpose, four functional areas and their dependencies.
2. `docs/DECISIONS.md` — validated decisions, constraints and open questions.
3. `HANDOFF.md` — documented progress, dated validation and remaining limits.

Identify the area concerned: EMPLOYEURS, CANDIDATS, CONSEILLERS, ADMIN or TRANSVERSE. Read the relevant implementation documentation and files before changing them. Report material consequences for the other areas; do not expand implementation scope without authorisation.

At significant milestones, update the relevant shared references within the authorised task scope. Record only supported facts and validated decisions; label proposals, uncertainties and unverified environment state explicitly. Preserve previous useful handoff information and distinguish historical test results from checks performed now. Never record secrets, real personal data or private FT procedures in these public documents.

These files are shared written context, not automatic access to every chat transcript. Their contents do not override the mandatory working rules below.

---

## Repository scope — standalone prototype

This repository contains the local Match Europe Django/PostgreSQL/Bootstrap prototype.
The historical Flask/Grist application stays in `eures-beta/eures-beta` and is not migrated here.
Employer page generation sources live in `scripts/employer-ui/`; browser styles live in `eures_beta/static/employer/`.
This prototype is shared for discussion and preservation; it must not be deployed as is.
Do not merge or deploy without separate explicit authorisation. Preserve `main` and work on branches.
Use fictional data for tests. Keep databases, sessions, keys, uploads and private FT procedures outside Git.
Local test integrations are opt-in; automated tests mock external requests.


---

# 1. BEFORE YOU CODE

Before modifying any code, check the following points.

## 1.1 Understand the requirement

- Identify precisely the feature, bug or task concerned.
- Do not expand the scope spontaneously.
- Do not refactor unrelated code.
- Do not modify another functional area only to "clean up" the project.
- When an important ambiguity exists, state the assumption being made before modifying a sensitive part of the system.

## 1.2 Verify the reference stack

The reference stack is:

- Django
- PostgreSQL
- Bootstrap

Prefer native Django functionality before adding an external dependency.

## 1.3 Verify the five structural requirements

Every user-facing feature must be designed from the beginning around the following five requirements:

1. FR / EN / DE
2. Security
3. Accessibility
4. Test quality
5. EURES / ELA brand compliance

A user-facing feature that does not satisfy these five requirements is not considered complete.

These requirements are structural and continuous. They are not final-stage checks.

## 1.4 Verify data and permissions

Before making a change:

- identify which data is read or modified;
- identify the roles concerned;
- verify permissions server-side;
- identify whether personal or sensitive data is involved;
- verify whether a PostgreSQL migration is required.

## 1.5 Verify business impact

For any change affecting candidates, employers, advisers or matching:

- preserve explainability;
- preserve human validation where required;
- do not introduce opaque automated decisions;
- do not interpret missing data as a negative criterion without an explicitly validated business rule.

## 1.6 Prepare validation

Before coding, identify:

- tests that must be added or adapted;
- FR / EN / DE translations required;
- accessibility checks required;
- permissions that must be tested;
- database migrations that may be required;
- EURES / ELA visual-brand implications for user-facing changes;
- documentation that may need to be updated.

---

# 2. MUST — TECHNICAL STACK

Match Europe uses the following reference stack:

- Django;
- PostgreSQL;
- Bootstrap.

The project must favour a simple and maintainable architecture.

The preferred application structure is:

Django → Django Templates → Bootstrap → PostgreSQL

JavaScript should be used where needed, but a major frontend framework must not be introduced without an identified requirement and prior validation.

Introducing another ORM, database, major frontend framework or structural infrastructure component must be explicitly justified and approved before implementation.

---

# 3. MUST — HOSTING AND CONFIGURATION

Hosting destinations and operational procedures belong in the private deployment repositories.

The application core must not depend directly on a particular hosting provider.

Environment-specific configuration must be managed through:

- environment variables;
- appropriate configuration files;
- deployment-compatible mechanisms.

Never hard-code:

- environment URLs;
- secrets;
- passwords;
- tokens;
- API keys;
- sensitive technical identifiers.

The project must remain runnable locally in an environment reasonably close to production.

---

# 4. MUST — INTERNATIONALISATION

Match Europe is a trilingual application.

The mandatory languages are:

- French — FR;
- English — EN;
- German — DE.

Every new user-facing feature must be available in all three languages before it is considered complete.

Use Django's internationalisation system.

Do not hard-code user-facing strings when they must be translatable.

This applies in particular to:

- pages;
- forms;
- error messages;
- validation messages;
- emails;
- notifications;
- help text;
- navigation;
- visible states and statuses.

A missing translation is considered a functional regression.

---

# 5. MUST — SECURITY

Security is a permanent requirement and not a finishing step.

Apply, in particular, the following principles:

- least privilege;
- server-side permission checks;
- personal-data protection;
- user-input validation;
- CSRF protection;
- secure session management;
- appropriate use of Django authentication mechanisms;
- systematic object-level access control;
- no secrets in Git;
- limited and maintained external dependencies;
- appropriate logging of sensitive actions.

Never assume that hiding something in the user interface protects the underlying data.

Permissions must always be enforced server-side.

Never place real personal data in:

- fixtures;
- tests;
- examples;
- screenshots;
- logs;
- demonstration files.

---

# 6. MUST — DATA PROTECTION

Collect only data required for a defined business purpose.

Prefer progressive data collection.

Do not request sensitive data before it is genuinely necessary.

Reuse information already provided when it is available and reliable.

Avoid unnecessary duplication of personal information.

Candidate and employer contact details must not be exposed prematurely in the journey.

Technical and audit logs must not become a hidden duplicate of the business database.

Any destructive or irreversible operation on real data requires explicit approval.

---

# 7. MUST — EXPLAINABLE MATCHING

Match Europe matching must remain explainable.

The reference business model is a weighted score out of 100 points.

The main dimensions are:

- job / job title;
- key skills;
- languages;
- mobility / location;
- availability / working conditions / driving licences or qualifications;
- salary.

Sub-scores must remain explainable.

Clearly distinguish between:

- weighted criteria;
- mandatory criteria;
- possible exclusion criteria.

Do not introduce an opaque score without explicit justification.

Do not automatically turn missing information into a penalty unless a validated business rule explicitly requires it.

Matching produces a recommendation.

It must not become an irreversible automated decision without explicit approval of that business-rule change.

---

# 8. MUST — HUMAN IN THE LOOP

Match Europe must preserve human validation in business processes where it is required.

The system may:

- calculate;
- suggest;
- rank;
- explain;
- prepare an introduction.

It must not automatically make a sensitive decision when the business process requires human validation.

Any increase in automation must preserve:

- understandability;
- traceability;
- explainability;
- the possibility of human intervention.

---

# 9. MUST — ROLES AND AUTHORISATION

Business roles must be explicitly distinguished.

At minimum:

- candidate;
- employer;
- adviser;
- administrator / operator.

Permissions must be defined according to both the user's role and the object concerned.

Never infer user rights only from the interface displayed to them.

Access-control rules should be centralised where reasonably possible and covered by tests.

---

# 10. MUST — ACCESSIBILITY

Accessibility is part of the Definition of Done.

Interfaces must, in particular:

- be usable with a keyboard;
- use semantic HTML;
- provide explicit form labels;
- maintain sufficient contrast;
- never communicate information through colour alone;
- provide appropriate text alternatives;
- remain usable with assistive technologies;
- work on mobile, tablet and desktop.

The minimum target is **WCAG AA**.

Bootstrap is a component foundation.

It does not replace accessibility review.

Avoid custom components when native HTML or Bootstrap already provides an appropriate accessible solution.

---

# 11. MUST — EURES / ELA BRAND GUIDELINES

## EURES / ELA brand guidelines

Match Europe is developed within the EURES context.

The official **EURES Graphic Guidelines 2022**, transmitted directly by EURES / ELA, are the authoritative visual-brand reference for the project.

Any work affecting the visual identity, user interface, public-facing pages, documents, presentations, communication assets, or partner co-branding must remain compatible with these guidelines.

In particular:

- respect the official EURES logo and its protection area;
- use EURES branding and colours consistently;
- preserve appropriate EURES prominence in co-branded materials;
- respect the distinction between jobseeker and employer visual universes where relevant;
- maintain at least WCAG AA accessibility and sufficient contrast;
- do not alter official EURES graphical elements or logos;
- Match Europe may have its own product identity, but it must remain visibly and coherently affiliated with EURES;
- do not invent or modify EURES branding rules;
- if a newer guideline or explicit instruction is provided by EURES / ELA, that newer instruction takes precedence.

The EURES Brand Book is a design authority, not a requirement to reproduce the 2022 templates literally.

Product UX, usability, accessibility and the Match Europe design system should modernise the implementation while staying within the EURES identity framework.

When in doubt about branding, preserve EURES compliance rather than creating a new visual convention.

EURES / ELA brand compliance applies to, among other things:

- application interfaces;
- authentication and onboarding pages;
- dashboards;
- public landing pages;
- forms;
- emails and notifications where visual branding is used;
- downloadable documents;
- reports;
- presentations;
- communication materials;
- social or campaign assets;
- partner-facing materials;
- co-branded content.

Match Europe may define and maintain its own product design system where useful, provided that it remains compatible with the authoritative EURES / ELA visual framework.

No implementation decision may redefine an official EURES logo, colour, graphical element, protection area, or branding rule.

---

# 12. MUST — TESTS

A feature is not complete if it is not sufficiently tested.

Test as appropriate:

- models;
- business logic;
- services;
- forms;
- validation;
- views;
- permissions;
- authentication;
- APIs;
- matching;
- internationalisation;
- critical migrations;
- important security behaviours.

Integration tests must use PostgreSQL where behaviour may differ from SQLite.

An important bug fix should, whenever reasonably possible, include a regression test reproducing the original issue.

A test must not merely verify that a page returns HTTP 200 when the underlying business behaviour is more complex.

---

# 13. SHOULD — DJANGO FIRST

Prefer native Django features before introducing an external library.

This applies especially to:

- ORM;
- migrations;
- forms;
- authentication;
- permissions;
- administration;
- sessions;
- CSRF protection;
- internationalisation;
- validation.

An external dependency should provide clearly identifiable value.

Avoid dependencies added only to save a few lines of straightforward code.

---

# 14. SHOULD — MODULAR ARCHITECTURE

Organise the project around coherent business domains.

Avoid:

- oversized views;
- models containing all business logic;
- functions with multiple unrelated responsibilities;
- duplicated business rules.

Important business rules should be isolated enough to be tested independently from the interface.

Avoid tightly coupling business logic to:

- HTML;
- the hosting provider;
- the email delivery system;
- external storage;
- a specific external API.

---

# 15. SHOULD — UX AND TRUST

Match Europe should minimise user friction.

Principles include:

- request only information that is useful at the point where it becomes useful;
- explain why data is requested;
- avoid unnecessarily long forms;
- reuse known information;
- avoid duplicate data entry;
- make journey steps understandable;
- favour progressive data collection.

When choosing between maximum immediate data collection and user trust, prefer the progressive journey by default.

Visual design should reinforce trust through consistency, clarity and appropriate affiliation with EURES.

---

# 16. SHOULD — AUDITABILITY

Significant business actions should make it reasonably possible to answer:

- who?
- what?
- when?
- on which object?

Do not unnecessarily store sensitive business values in logs.

Prefer stable and understandable technical references.

Audit logs must not contain secrets or unnecessary personal information.

---

# 17. CONVENTION — GIT AND COLLABORATIVE WORK

Do not work directly on the main branch when the project workflow uses branches and pull requests.

Prefer:

- one branch per coherent task;
- understandable commits;
- reasonably sized pull requests;
- targeted changes.

Do not include in a pull request:

- unrelated refactoring;
- unnecessary mass renaming;
- formatting changes to unrelated files;
- generated files without a clear reason.

Any database migration must be clearly identified.

Any change to an API contract must be explicitly documented.

Any deliberate change to the Match Europe visual design system that may affect EURES / ELA compliance must be clearly identified in the pull request.

---

# 18. CONVENTION — AI AGENTS

An AI agent must remain strictly within the scope of the requested task.

It must not spontaneously:

- rewrite a large part of the project;
- change framework;
- change database;
- replace Bootstrap;
- add an external service;
- modify an approved architecture;
- redefine EURES / ELA visual-brand rules;
- alter official EURES assets;
- remove code it considers unnecessary without checking its role;
- perform global refactoring.

An agent must never silently bypass a rule in this file.

If an agent believes that a rule prevents a correct implementation, it must explain the conflict before introducing an exception.

If visual-brand guidance is ambiguous, the agent must preserve known EURES compliance rather than inventing a new convention.

---

# 19. BEFORE YOU FINISH

Before considering a task complete, verify all of the following.

## Functional

- The requested feature is actually complete.
- Existing behaviour has not been unintentionally broken.
- The initial scope has been respected.

## Internationalisation

- User-facing content exists in FR.
- User-facing content exists in EN.
- User-facing content exists in DE.
- No important user-facing text is hard-coded outside the translation system.

## Security

- Permissions are checked server-side.
- New user inputs are validated.
- No secret has been added to the repository.
- Logs do not unnecessarily expose sensitive information.
- Unauthorised-access scenarios have been tested where relevant.

## Accessibility

- The interface is keyboard accessible.
- Form fields have appropriate labels.
- HTML structure is coherent and semantic.
- Error messages are understandable.
- Information is not conveyed through colour alone.
- Responsive behaviour remains usable.
- WCAG AA requirements are respected where applicable.

## Tests

- Existing relevant tests pass.
- Significant new behaviour is tested.
- Permissions are tested where relevant.
- Important error cases are tested.
- PostgreSQL is used for tests that may depend on database-engine behaviour.

## EURES / ELA brand compliance

For any user-facing or communication-related change:

- EURES / ELA brand requirements have been considered;
- official EURES graphical assets have not been altered;
- official logo protection requirements are respected where relevant;
- branding and colours remain compatible with the official guidelines;
- EURES prominence remains appropriate in co-branded materials;
- the visual treatment remains consistent with the relevant jobseeker or employer universe where applicable;
- Match Europe remains visibly and coherently affiliated with EURES;
- accessibility has not been sacrificed for visual-brand conformity;
- no new EURES branding rule has been invented.

## Database

- Required migrations have been created.
- Migrations work from a clean state.
- No unapproved destructive migration has been introduced.

## Quality

- No obvious dead code has been created.
- Added dependencies are genuinely necessary.
- Code remains readable.
- Relevant documentation has been updated where necessary.

---

# 20. DEFINITION OF DONE

A Match Europe user-facing feature is considered complete only if:

1. it satisfies the functional requirement;
2. it works with PostgreSQL;
3. it respects permissions and access-control rules;
4. it respects security requirements;
5. it respects accessibility requirements;
6. it is available in FR, EN and DE;
7. it complies with the applicable EURES / ELA brand guidelines;
8. it has appropriate tests;
9. the relevant tests pass;
10. no sensitive information or secret has been added to the repository;
11. any database migrations are controlled and understood;
12. required documentation is up to date.

The five permanent quality pillars for every user-facing feature are:

1. **FR / EN / DE**
2. **Security**
3. **Accessibility**
4. **Test quality**
5. **EURES / ELA brand compliance**

**A feature missing any of these five pillars is not considered complete.**
