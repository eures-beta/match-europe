# Procédures de travail des agents

Ce guide décrit le fonctionnement actuel du dépôt. Il n'est pas une archive ni
un mandat de fusion/déploiement. Les règles impératives restent dans
[AGENTS.md](../AGENTS.md), chargé avant les procédures spécialisées.

## Choisir les références utiles

- Modification Python, service ou modèle : skill
  [django-change](../.agents/skills/django-change/) puis guide du domaine.
- Interface, texte ou e-mail : skill
  [interface-change](../.agents/skills/interface-change/) puis
  composants Bootstrap existants, gettext et contrôles HTML/CSS/JS.
- Rebase, refresh ou fusion autorisée : skill
  [stack-maintenance](../.agents/skills/stack-maintenance/).
- Ouverture de PR : skill
  [pull-request-opening](../.agents/skills/pull-request-opening/), template courant,
  aperçus et vérifications de pile juste avant puis après création.
- Diagnostic de production : commandes existantes du dépôt privé de déploiement,
  sans copier des secrets ni créer de script d'accès ad hoc dans ce dépôt.

Ces skills sont des procédures réutilisables à charger selon la tâche.
Leur sélection automatique dépend de l'outil ; une équipe peut les invoquer
explicitement. Aucune lecture automatique d'un document arbitraire n'est promise.

## Préparer et valider un changement Django

Identifier rôle, opérations autorisées/interdites, données, stockage transitoire
et durable, services externes et migrations. Un brouillon de session n'est pas
un profil durable ; une revue d'offre n'est pas une conversation à trois.
Consulter [les décisions](DECISIONS.md) et les [retours pertinents](AGENT_FEEDBACK.md)
avant de prolonger un ancien prototype.

Utiliser un worktree, un environnement et une base propres. Voir
[la préparation PostgreSQL](DEVELOPPEMENT.md) et [les tests](TESTS.md).
Une erreur de configuration doit être expliquée ; ne pas basculer silencieusement
vers un autre compte, une autre base ou une simulation.

Réutiliser les services et validations métier, hors couche web.
Ne pas ajouter une bibliothèque pour quelques lignes déjà couvertes par Django.
Pour les migrations : préserver les données existantes et permissions,
ne pas réécrire une migration publiée et éprouver le retour arrière quand applicable.
Les identifiants cryptographiques/protocolaires ne sont pas des libellés à remplacer
aveuglément ; documenter leur compatibilité.

Une régression importante reproduit le comportement avant correction lorsque possible.
Les tests vérifient les parcours et refus dans les trois environnements avec des
données ordinaires fictives, pas seulement le mode de démonstration.
Simuler les frontières externes, jamais la logique métier qu'on cherche à valider.

## Interface et marque

Cinq exigences ensemble : FR/EN/DE, sécurité, accessibilité, tests et EURES/ELA.
Réutiliser Bootstrap et les tokens/composants plutôt qu'une palette parallèle.
Les EURES Graphic Guidelines 2022 transmises par EURES/ELA font autorité :
logos intacts, zones de protection, affiliation claire et distinction des univers
candidat/employeur. Une consigne officielle plus récente prévaut.
Cela couvre interfaces, e-mails, documents et communications ; le design system
modernise l'implémentation sans redéfinir les règles officielles.

Conserver clavier, labels, contrastes, alternatives et responsive.
Favoriser les composants HTML natifs. Collecter progressivement les données utiles,
expliquer les étapes et préserver la confiance plutôt qu'exiger tout d'emblée.

Un seul template traduit, messages gettext jusqu'aux erreurs et JavaScript.
CSS externe ; exceptions d'e-mails et catalogue uniquement selon [HTML/CSS](HTML_CSS.md).
Black pour Python, djLint pour HTML, Prettier pour JS/CSS : leurs contrôles ne
garantissent pas seuls la qualité du parcours, du sens ou de l'accessibilité.
Signaler les vérifications visuelles/manuelles réellement réalisées et restantes.

## PR, revue et livraison

À chaque entretien de pile et avant livraison, examiner
[les routes vestiges et leurs échéances](LEGACY_ROUTES.md). Leur compatibilité
dure 30 jours après retrait déployé ; élaguer les groupes échus dans un commit
dédié, sans remettre le compteur à zéro lors d’un rebase ou d’une retouche.

Pour enregistrer une description, utiliser `make pr-description PR=…`, puis lire
le fichier annoncé. Vérifier le succès avant toute étape dépendante ; un échec
invalide l'ancienne copie. Voir [le contrat](PR_DESCRIPTION.md).
Pour GitHub Actions, utiliser `make ci-status RUN=…` puis `make ci-errors RUN=…` ;
réutiliser le cache des logs terminés. Voir [les paramètres](CI_DIAGNOSTICS.md).
Ces lectures ne donnent aucune autorisation de relance ou de fusion.

Lire le [template commun](https://github.com/eures-beta/.github/blob/main/pull_request_template.md)
avant de rédiger/modifier une description. Garder les sections pertinentes,
en français ; remplacer les aides et distinguer nouveaux/modifiés modèles/apps,
données sauvegardées, migrations, preuves exécutées et limites.
Assigner au demandeur identifié ; relecture `dejafait`, sans prétendre qu'une
auto-demande refusée a été enregistrée.

Une PR correspond à un changement cohérent. Conserver les auteurs et commits ;
pas de merge commit, squash seulement sur demande. Pendant revue, ne pas rebaser
spontanément ; avant fusion autorisée, destination à jour, rebase et validations.
Si GitHub impose une opération native de pile, respecter les règles de protection,
sans bypass ni présentation d'une intention comme une fusion réussie.

Après conflit, vérifier le sens du changement et réappliquer les qualités héritées,
dans un commit distinct si utile. Une validation ancienne ne vaut pas preuve du
nouveau SHA ; les CI ignorées ou annulées ne prouvent ni succès ni défaut du code.
Vérifier les vrais jobs du SHA courant, en particulier le push après #209.

Après une livraison autorisée, vérifier le commit réellement servi et la santé,
pas seulement l'état « merged ». Retargeter les descendantes directes et vérifier
leurs diffs. Ne supprimer une branche que si aucune PR ne s'en sert encore.
Pas de rafraîchissement des branches indépendantes sans demande.

## Documentation et transmission

Conserver le rôle des dossiers et chaque fichier dans leurs README, avec liens
vers les dossiers de sous-navigation et vers les fichiers eux-mêmes.
Les règles durables vont dans AGENTS/décisions, les procédures dans leurs guides,
les points de reprise dans le handoff et les retours dans leur registre.
Supprimer le détail obsolète après intégration : [Git est l'archive](DOCUMENTATION.md).
Ne pas augmenter un plafond pour conserver une chronologie ou dupliquer des règles.

La transmission exige un dépôt actualisé et une lecture effective. Le registre
des retours n'envoie pas de message à une IA ni à une session inactive.
Un contrôle CI et un test de régression sont préférables à une nouvelle répétition
de la même instruction. N'exécuter aucune action externe non autorisée pour
« communiquer » un retour.
