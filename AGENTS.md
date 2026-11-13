# Match Europe — consignes communes

## Avant chaque tâche

- Travailler sur une branche `codex/`, dans le périmètre demandé ; ne pas modifier
  `main`, une branche d'une autre session ou un environnement sans autorisation.
- Sur une reprise, lire les consignes de la branche et leurs évolutions sur
  `main`. Une ancienne branche ou session ne reçoit pas magiquement les nouveautés.
- Lire [la vue d'ensemble](docs/VUE_ENSEMBLE.md), [les décisions actuelles](docs/DECISIONS.md)
  et [la reprise](HANDOFF.md). Identifier le rôle concerné : candidat, employeur,
  conseiller, administration ou transverse.
- Lire les guides, [retours](docs/AGENT_FEEDBACK.md) et [skills](.agents/skills/)
  utiles ; voir le [guide des agents](docs/AGENT_WORKFLOW.md).
- Distinguer faits, décisions, propositions et preuves historiques ; ces fichiers
  n'autorisent aucune fusion ni accès aux conversations privées.

## Règles essentielles

- Stack : Django, PostgreSQL, templates Django et Bootstrap ; privilégier Django
  natif. Pas de nouveau framework, ORM, service ou changement architectural non demandé.
- Les fonctionnalités métier fonctionnent en local, recette et production avec
  les mêmes contrôles. Ne pas les conditionner au mode démo, à une IP locale,
  à une adresse fictive ou à la désactivation des e-mails.
- Une interdiction de fusionner/déployer vise l'action de l'agent, jamais le
  fonctionnement du code. Les services restent configurables ; un service absent
  donne un état explicite ou le repli prévu, pas une simulation silencieuse.
- `ALBERT_SIMULATED` est explicite et désactivé par défaut.
  `EMAIL_DELIVERY_ENABLED` est l'unique autorisation d'envoi, avec le transport configuré.
  Tous les e-mails passent par le backend Django commun, jamais par un accès direct.
- `DEMO_ACCOUNTS_ENABLED` concerne seulement les comptes et données fictifs :
  local/recette, base fictive, envoi réel désactivé ; jamais en production.
  Ces protections ne doivent pas restreindre un parcours métier.
- Vérifier côté serveur authentification, rôle actif, propriété, consentement,
  CSRF et validité des données. Pas de droits déduits de l'interface ou d'une IP.
- Tous les conseillers actifs ont les mêmes droits métier, sans habilitation
  Django individuelle ni groupe supplémentaire. Cela ne donne aucun droit admin.
- L'admin Django est en consultation, même pour les superutilisateurs : pas
  d'ajout, modification, suppression ou action groupée ; utiliser `users/admin_base.py`.
- Connexion : seulement un compte existant actif, jamais de création implicite.
  Conseillers/employeurs : invitation explicite ; candidat : vérification du lien
  puis confirmation POST avant création du compte/profil. Ne pas convertir un autre rôle.
- Les rôles candidat/employeur/conseiller sont distincts ; email unique sans casse,
  rôle obligatoire et immuable. Voir [le modèle utilisateur](docs/USER_MODEL.md).
- Aucun secret, donnée personnelle réelle, dump, session, document privé ou accès
  serveur dans Git, fixtures ou logs. Les destinations et procédures de production
  restent dans les dépôts privés ; les tests simulent les services externes.
- Ne collecter que l'utile ; pas de contact candidat/employeur exposé prématurément.
  Pas de destruction de données réelles sans autorisation explicite.
- Le matching est explicable et conserve la décision humaine, les inconnus et les
  consentements distincts. Pas de nouveaux poids, pénalités ou rejets opaques non validés.
- Chaque fonctionnalité visible respecte FR/EN/DE, sécurité, accessibilité WCAG AA,
  tests pertinents et identité EURES/ELA. Les cinq exigences sont obligatoires.
- Utiliser un template commun et gettext, pas une copie HTML par langue.
  Tous les messages visibles, y compris JavaScript, erreurs et e-mails, sont traduits.
- Avant une interface, lire [le design system](docs/DESIGN_SYSTEM.md) : Bootstrap,
  tokens ECL/EURES, composants communs. Les EURES Graphic Guidelines 2022 font autorité ;
  ne pas réinventer les logos, couleurs ou règles officielles.
- Clavier, labels, sémantique HTML, contrastes, alternatives et responsive sont
  nécessaires ; une information ne repose jamais uniquement sur la couleur.
- Vues, formulaires et routes web dans `eures_beta/www/` ; modèles, migrations
  et services dans les applications métier, sans dépendance vers la couche web.
  Garder les validations partagées dans le domaine ; éviter les duplications.
- Aucun dossier `scripts/` racine. Les outils vont dans leur domaine ou un paquet
  transverse explicite ; les tests Python/JS et leurs fixtures dans `tests/` par domaine.
- Renommer ensemble modèle, fichiers, relations, colonnes et objets SQL ; conserver
  données, droits et migrations historiques. Vérifier `make check` et l'aller-retour
  PostgreSQL ; [convention](docs/MODEL_NAMING.md). Traiter la cryptographie à part.
- Routes anglaises nommées et indépendantes des templates/langues ; utiliser
  `reverse` ou `{% url %}`. Les alias historiques ne sont plus émis et restent
  isolés dans `www/public/legacy_urls.py`, leurs helpers et tests de compatibilité.
  Préserver méthode HTTP, corps, CSRF et droits dans une redirection.

## Commandes et validation

- GitHub : `make pr-description PR=…`, puis lire le fichier produit ; CI :
  `make ci-status RUN=…` et `make ci-errors RUN=…`. Voir le guide des agents.
- Python vient de `.python-version` ; suivre [sa maintenance](docs/PYTHON_RUNTIME.md),
  sans recopier une version dans Make, CI ou Docker.
- Toute opération récurrente ou complexe passe par une cible Make lisible et
  documentée ; README et descriptions de PR montrent cette cible, pas sa longue recette.
  Les diagnostics ponctuels simples et Git/GitHub peuvent rester directs.
- Une seule entrée Django : `make run PORT=…`. Tests : `make test`,
  `make test TESTS=module.Classe.methode` ou `TEST_ARGS='-k motif'` ;
  JavaScript : `make test-js JS_TESTS=chemin.test.cjs`. Pas de cible par catégorie de test.
- Chaque worktree a son `.venv` (`make install-test`), son `.env` ignoré et sa base
  `PGDATABASE` unique. `PGHOST`, `PGPORT`, `PGUSER` sont explicites.
  Réutiliser le serveur/rôle identifié, jamais des identifiants de production.
- `make db-check` diagnostique ; `make db-create` prépare la seule base locale
  absente. `make test` exécute le précontrôle. Pas de création de rôle, attribution
  de droits, arrêt d'un serveur partagé ou recherche automatique d'un autre compte.
- Lancer les commandes Make directement, avec le répertoire de travail de l'outil,
  sans wrapper ou redirection inutile. Ne jamais masquer une action dans Make
  pour contourner une approbation ; conserver les contrôles de permissions du client.
- Valider le comportement réel et les refus d'accès, pas seulement HTTP 200.
  Corriger le contrat d'un test erroné ; ajouter une régression pour un bug important.
  Utiliser PostgreSQL, tester les migrations et les données non vides quand pertinent.
- Avant publication : `make check`, tests adaptés, Black, djLint HTML,
  Prettier JS/CSS, syntaxe JS et gettext. Voir [les tests](docs/TESTS.md).
  `make docs-check` contrôle les budgets documentaires, y compris les nouveaux AGENTS/skills.
- CSS web externe via `{% static %}`, Bootstrap/tokens d'abord. Pas de bloc
  `<style>` ni d'attribut `style`. Exceptions limitées aux e-mails HTML et aux
  attributs dynamiques du catalogue design-system, jamais à une page métier.
  `make format-html-check` applique djLint H021/C901 ; pas de contournement `djlint:off`.
- Black ne formate pas HTML/JS/CSS. Voir [HTML](docs/HTML_FORMATTING.md),
  [séparation CSS](docs/HTML_CSS.md) et [JavaScript](docs/JAVASCRIPT_FORMATTING.md).

## Collaboration, documentation et publication

- Les descriptions de PR sont en français selon le
  [modèle commun](https://github.com/eures-beta/.github/blob/main/pull_request_template.md),
  à lire avant édition. Assigner au demandeur identifié et demander la relecture
  à `dejafait` ; signaler les refus.
- Décrire le rôle utilisateur, changements, données/modèles/migrations, tests
  exécutés et limites. Si le modèle est inaccessible, le signaler et utiliser
  Pourquoi, Comment, À vérifier, Comment tester, sans inventer son contenu.
- Une création/relecture de PR n'autorise ni fusion ni déploiement. Pas de merge
  commit, ni squash sans demande. Avant fusion autorisée : destination à jour,
  rebase, résolution revue et contrôles réussis ; réécriture par lease explicite.
- Pas de rebase automatique pendant une revue, sauf demande/préparation de fusion.
  Préserver commits concurrents, auteurs, brouillons et comportement après conflit.
  Ne pas modifier une autre PR indépendante sous prétexte de rafraîchissement.
- Après fusion, retargeter les descendantes directes et vérifier leur diff.
  Supprimer une branche fusionnée seulement si elle n'est plus nécessaire.
  Au point quotidien demandé, maintenir une pile d'actives sans essais, backups ou PR fusionnées ;
  pas de surveillance en arrière-plan. Voir le skill de maintenance de pile.
- Mettre à jour les README des dossiers touchés : rôle, liens vers les sous-dossiers
  (pas leurs README), fichiers et descriptions. Garder les guides spécifiques cohérents.
- `HANDOFF.md` décrit seulement la reprise actuelle ; `DECISIONS.md` garde les
  choix durables et leur pourquoi. Statuts vérifiés et limites datés, jamais de succès promis.
- Git et les PR archivent les anciennes versions : pas de fichier d'archives
  ni de recopie chronologique. Remplacer une décision en expliquant ce qu'elle supplante.
  Les guides actuels ne doivent pas affirmer une ancienne restriction.
- Les retours génériques utiles vont dans `docs/AGENT_FEEDBACK.md` avec exemple,
  règle et vérification ; pas de procès personnel ni de transcript privé.
  Déplacer un retour résolu vers un guide/test pertinent puis retirer l'entrée.
- Les plafonds de `docs/DOCUMENTATION.md` sont des maxima, pas des objectifs.
  Scinder par sujet utile plutôt qu'augmenter le budget ou multiplier les consignes globales.
