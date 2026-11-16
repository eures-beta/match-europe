# Triage des alertes CodeQL

Une alerte signale un chemin à examiner, pas une exploitation démontrée. Les
numéros ci-dessous sont ceux de l'onglet Security, pas des issues ou des PR.
La liste porte sur les 18 alertes initiales du 16 novembre 2026 ; l'état réel
reste dans GitHub, et non dans ce document.

## Extraction des documents

[Service](../eures_beta/documents/) et [tests](../tests/documents/).
Exécuter `make test TESTS=tests.documents`.

| Alerte | Traitement et preuve |
| --- | --- |
| [4](https://github.com/eures-beta/match-europe/security/code-scanning/4) | Commission suivie de `%` : recherche du dernier pourcentage puis d'un mot, sans wildcard réessayé. |
| [5](https://github.com/eures-beta/match-europe/security/code-scanning/5) | Expérience requise : première occurrence puis recherche du qualificatif dans la suite, ordre et casse conservés. |
| [6](https://github.com/eures-beta/match-europe/security/code-scanning/6) | URL imprimée avec pagination : découpage du dernier `/` et chiffres décimaux Unicode, sans retour arrière. |
| [7](https://github.com/eures-beta/match-europe/security/code-scanning/7) | `fullmatch` de deux suites de chiffres séparées par `/` : recherche ancrée simple, pas le scan non ancré supposé. |
| [8](https://github.com/eures-beta/match-europe/security/code-scanning/8) | La recherche dans l'en-tête vient après `len(line) < 125`. Test vérifiant ce court-circuit. |
| [9](https://github.com/eures-beta/match-europe/security/code-scanning/9) | Séparation entreprise : suites d'espaces supprimées avant la regex. Test du nom extrait et des lignes normalisées. |
| [10](https://github.com/eures-beta/match-europe/security/code-scanning/10) | Expérience : même normalisation préalable ; test de conservation de `3 + years minimum`. |
| [11](https://github.com/eures-beta/match-europe/security/code-scanning/11) | Langues : même normalisation préalable ; test de conservation de `English : B2`. |
| [12](https://github.com/eures-beta/match-europe/security/code-scanning/12) | Paragraphes : lignes normalisées jointes par un espace ; test du découpage des tâches. |

Les tests couvrent aussi de longues entrées répétitives dans un sous-processus
avec délai maximal, sans seuil de quelques millisecondes dépendant de la machine.
La limite d'import de 16 000 caractères et l'authentification ne suffisent pas à
justifier les anciennes regex 4–6 : le traitement des champs se fait dans le
processus web après la lecture PDF isolée. Les protections 8–12 sont existantes :
ne pas les retirer lors d'une réorganisation du parseur.

## Autres remontées initiales

- Recherche métiers : [3](https://github.com/eures-beta/match-europe/security/code-scanning/3),
  [13](https://github.com/eures-beta/match-europe/security/code-scanning/13),
  [14](https://github.com/eures-beta/match-europe/security/code-scanning/14),
  [15](https://github.com/eures-beta/match-europe/security/code-scanning/15).
  La requête API est bornée à 150 caractères. Leur simplification relève de la
  PR distincte sur le catalogue ; ce document ne prétend pas les corriger.
- [1](https://github.com/eures-beta/match-europe/security/code-scanning/1) : le puits
  est la propriété DOM `href` d'un lien vers une origine HTTPS OpenStreetMap fixe,
  pas un parseur HTML ; les paramètres de recherche sont encodés. L'injection de
  coordonnées dans le fragment ne peut pas modifier le protocole ou l'origine.
- [2](https://github.com/eures-beta/match-europe/security/code-scanning/2) : fixture
  Docker, `SSLContext(PROTOCOL_TLS_SERVER)`, minimum TLS 1.2 avec Python 3.14.
  Ce contexte ne définit pas le HTTPS de production.
- [16](https://github.com/eures-beta/match-europe/security/code-scanning/16) :
  redirection candidat vers un chemin interne fixe ; langue autorisée et étape
  validée ou issue de l'état serveur.
- [17](https://github.com/eures-beta/match-europe/security/code-scanning/17) :
  `target_language` appartient à `fr`, `en`, `de` avant la redirection interne.
- [18](https://github.com/eures-beta/match-europe/security/code-scanning/18) :
  retour après connexion validé par une liste de destinations internes fixes ;
  le défaut est une route Django, pas une URL fournie par le client.

## Liens, résolution et justification

La description de chaque PR donne les URL complètes des alertes concernées,
les corrections et les tests. Ne pas écrire `Fixes #4` : ce numéro désignerait
une issue, pas l'alerte de sécurité 4. Un lien Markdown ne prouve ni correction
ni association native dans GitHub.

GitHub expose les branches et PR associées dans la section **Development** de
l'alerte. Vérifier ce qui apparaît après l'analyse ; les API publiques consultées
ne proposent pas de mutation générale pour y rattacher une PR manuelle.
Le statut de la branche par défaut reste ouvert jusqu'à l'intégration et au
passage de CodeQL : ne pas écarter une alerte réelle pour rendre une PR verte.

Pour un classement sans suite, le menu **Dismiss alert** permet de choisir un
motif et d'ajouter un commentaire. L'API fournit `dismissed_reason` et
`dismissed_comment` : y enregistrer la preuve, les limites et un lien vers la PR
ou ce guide versionné. Utiliser **false positive** pour un chemin incorrect et
**mitigated** pour un risque déjà empêché par une protection démontrée. Aucun
ignore global de règle ou de dossier. Réouvrir si les hypothèses changent.

Références : [résolution](https://docs.github.com/en/code-security/how-tos/manage-security-alerts/manage-code-scanning-alerts/resolve-alerts),
[détails des alertes](https://docs.github.com/en/code-security/concepts/code-scanning/code-scanning-alerts),
[API](https://docs.github.com/en/rest/code-scanning/code-scanning#update-a-code-scanning-alert),
[TLS Python](https://docs.python.org/3.14/library/ssl.html#ssl.SSLContext).

Pour les opérations répétées, utiliser `make security-alerts`,
`make security-plan FILE=…`, puis `make security-apply FILE=…` après revue du plan.
[Le guide de l’outil](SECURITY_ALERTS.md) détaille les justifications individuelles,
les contrôles de concurrence et la reprise après échec, sans changer ce triage.
