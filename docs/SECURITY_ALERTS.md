# Consulter et mettre à jour les alertes de sécurité

L’outil `config.security_alerts` gère les décisions explicites de l’équipe sur
les alertes CodeQL de `eures-beta/match-europe`. Il utilise `gh` déjà authentifié,
la bibliothèque standard Python, sans Django, base, nouveau secret ni shell
intermédiaire. Il ne décide jamais qu’une alerte est un faux positif.

## Trois commandes

```bash
make security-alerts
```

Cette lecture retourne du JSON : numéros, état et métadonnées du code analysé.
Choisir les alertes à traiter, recopier leur bloc `expected` sans le modifier,
puis remplir `state`, `reason` et `comment` dans un fichier local. La sortie
initiale contient des décisions vides, volontairement impossibles à appliquer.
Les alertes déjà corrigées (`fixed`) sont omises, pas transformées en classements.

```bash
make security-plan FILE=/private/tmp/decisions.json
```

Cette commande relit GitHub, valide tout le fichier et montre les modifications,
sans écrire. Exemple fictif de structure, à remplacer par les métadonnées réelles :

```json
{
  "repository": "eures-beta/match-europe",
  "alerts": [{
    "number": 12345,
    "expected": {
      "state": "open",
      "rule_id": "py/example-rule",
      "path": "fictional/module.py",
      "commit_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "ref": "refs/heads/main",
      "start_line": 42,
      "dismissed_reason": null,
      "dismissed_comment": null
    },
    "state": "dismissed",
    "reason": "false positive",
    "comment": "Justification vérifiée et lien vers la preuve ou la PR."
  }]
}
```

Les motifs acceptés sont ceux de GitHub : `false positive`, `mitigated`,
`used in tests`, `won't fix`. Le commentaire individuel est obligatoire et limité
à 280 caractères : expliquer brièvement le constat, puis lier la preuve détaillée.
Une correction de code n’autorise pas à classer artificiellement une alerte :
laisser CodeQL constater la correction après intégration.
Pour réouvrir : `state: "open"`, `reason: null`, avec une justification dans le plan.
Cette justification de réouverture est affichée localement ; seul l’état est
transmis à GitHub, sans écraser l’ancien commentaire de classement.

```bash
make security-apply FILE=/private/tmp/decisions.json
```

L’invocation autorisée de cette commande applique le fichier : pas de question
interactive supplémentaire dans l’outil. Elle vérifie **tout** le plan avant le
premier PATCH, puis relit chaque alerte juste avant son écriture. État, motif,
commentaire, règle, fichier, ligne, référence et commit analysé sont contrôlés.
Si le code ou la décision a changé, refaire la revue au lieu de remplacer
aveuglément les métadonnées attendues. Maximum 50 alertes par plan.

## Échecs, reprise et autorisations

Chaque succès produit un reçu JSON avec le numéro et l’état confirmé. L’API
n’offre pas de transaction entre alertes : en cas d’échec, les premières décisions
peuvent avoir été appliquées. L’outil s’arrête sans réessai automatique ; consulter
les reçus et GitHub, puis reprendre le même fichier. Les décisions déjà identiques
sont ignorées. Une dernière course entre GET et PATCH reste possible : ce n’est
pas un verrou ni une garantie de comparaison atomique côté GitHub.

Le dépôt et les endpoints sont fixes ; aucun paramètre n’exécute une autre
commande, ne change les permissions, n’approuve une demande de classement et ne
contourne les protections GitHub. Les commentaires passent en JSON par stdin,
pas dans une longue ligne shell. Les chemins Make sont transmis comme données.
Ne pas placer de secret ou de donnée personnelle dans le plan ou les commentaires.

Une autorisation persistante du client peut viser `make security-apply`, plutôt
qu’un numéro d’alerte et une justification uniques. Elle reste distincte des
restrictions réseau du client et des droits GitHub : aucune règle globale n’est
installée par cet outil. Les lectures peuvent être autorisées séparément.

Tests hors réseau : `make test TESTS=tests.config.test_security_alerts`.
Voir [le triage CodeQL](CODEQL_TRIAGE.md) et
[l’API officielle GitHub](https://docs.github.com/en/rest/code-scanning/code-scanning#update-a-code-scanning-alert).
