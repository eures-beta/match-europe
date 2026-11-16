# Documentation actuelle et budgets

## Répartition

| Fichier | Contenu à garder | Maximum UTF-8 / lignes |
| --- | --- | --- |
| `AGENTS.md` racine | Règles impératives et orientation | 10 Kio / 180 |
| `HANDOFF.md` | Prochaine reprise, limites ouvertes, liens PR | 6 Kio / 100 |
| `docs/DECISIONS.md` | Choix actuels, justification et références | 10 Kio / 160 |
| `docs/VUE_ENSEMBLE.md` | Produit, rôles et domaines actuels | 6 Kio / 100 |
| `docs/AGENT_FEEDBACK.md` | Retours actionnables encore utiles | 8 Kio / 140 |
| Ce guide et `AGENT_WORKFLOW.md` | Entretien et procédures transverses | 8 Kio / 140 chacun |
| Autre `AGENTS.md` ou `AGENTS.override.md` | Règles spécifiques au sous-arbre | 4 Kio / 80 |
| Chaque `SKILL.md` du dépôt | Procédure ciblée, références pertinentes | 4 Kio / 90 |

Un Kio vaut 1 024 octets ; les accents comptent en UTF-8, pas comme un seul octet.
La chaîne d'AGENTS applicables à un dossier reste sous 20 Kio, overrides compris.
Ce budget réserve de la marge sous la limite Codex par défaut de 32 Kio ;
il ne prouve pas ce qu'un autre outil charge ni ce qu'un agent a effectivement lu.

Ces maxima ne sont pas des objectifs. Les guides techniques, licences tierces
et catalogues n'ont pas un plafond uniforme : scinder un guide quand cela améliore
sa consultation, pas pour contourner un budget des documents chargés systématiquement.
Ne pas créer de nouveau fichier global de consignes pour déborder ces limites.

## Entretien

- Au début d'une tâche, lire les documents courts communs puis seulement les
  guides/retours/skills du sujet. Au retour sur une ancienne branche, vérifier
  les changements de consignes de main avant d'agir.
- Mettre à jour l'état actuel plutôt qu'ajouter une nouvelle entrée datée à chaque
  résultat de test. Les PR et la CI portent les SHA, comptes de tests et journaux.
- Après intégration, retirer du handoff le travail terminé et mettre à jour son
  guide métier. Garder ici les limites qui changent réellement la prochaine reprise.
- Une décision importante conserve son pourquoi et sa référence. Quand elle est
  remplacée, écrire le contrat actuel et citer ce qu'il remplace ; ne pas laisser
  deux règles contradictoires présentées comme simultanément applicables.
- Un retour indique symptôme, exemple vérifiable, comportement attendu et contrôle.
  Une fois absorbé par un guide/test, supprimer le détail devenu inutile.
- Actualiser les README des dossiers touchés ; liens de navigation vers les dossiers,
  liens de fichiers vers les fichiers, avec une phrase décrivant leur rôle.
- Aucune donnée personnelle réelle, secret, transcript privé ou procédure
  d'exploitation interne dans les documents publics.

## Archive : Git et les PR

Pas de fichier `*_ARCHIVE.md`, ni de copie de l'ancien AGENTS ou handoff.
L'[historique Git](https://github.com/eures-beta/match-europe/commits/main) conserve
les versions et les [PR](https://github.com/eures-beta/match-europe/pulls?q=is%3Apr)
les raisons et validations. Ajouter un lien ciblé à une PR utile plutôt que recopier
son compte rendu. Une correction documentaire ne réécrit pas l'histoire Git.

## Contrôle

`make docs-check` vérifie les fichiers requis, les tailles, les lignes et le cumul
des AGENTS/overrides par dossier. Le contrôle utilise seulement la bibliothèque
standard Python, sans Django, base, réseau ou mutation.
Il est exécuté par la CI qualité et par `make check`.

Un dépassement échoue avec le chemin, la taille et la limite. Réduire les répétitions,
actualiser les décisions ou déplacer une procédure dans un guide ciblé ;
une hausse de budget reste une modification explicite à justifier en revue.
Ne pas tronquer automatiquement le texte : les règles utiles doivent être préservées.

Les skills du dépôt sont dans [ce dossier](../.agents/skills/).
Codex découvre leurs métadonnées puis charge les instructions du skill sélectionné.
Ils ne remplacent ni les règles impératives du fichier racine ni une autorisation
d'agir, et leur présence ne garantit pas la notification d'une session déjà ouverte.
