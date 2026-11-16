# Retours de revue pour les agents

Consulter les entrées du sujet avant de développer. Ce registre décrit des
problèmes du code et du processus, pas les intentions ou l'identité d'une IA.
Les exemples peuvent avoir été corrigés depuis : vérifier le code courant.
Les retours absorbés par les guides/tests sont à raccourcir ou retirer ;
Git conserve leur histoire. Voir [la politique documentaire](DOCUMENTATION.md).

## F01 — Une fonctionnalité métier n'est pas une recette

**Exemples :** restrictions historiques des
[#154](https://github.com/eures-beta/match-europe/pull/154),
[#157](https://github.com/eures-beta/match-europe/pull/157),
[#158](https://github.com/eures-beta/match-europe/pull/158) et
[Push #192](https://github.com/eures-beta/match-europe/pull/192).

**Attendu :** même parcours métier local/recette/production, avec rôle, propriété,
CSRF, consentements et configuration de service. Aucun accès accordé par IP locale,
mode démo, adresse fictive ou e-mails désactivés.
Les comptes fictifs et leurs outils restent explicitement interdits en production :
ne pas supprimer cette protection en corrigeant une restriction métier.

**Contrôle :** tests positifs et négatifs dans les trois environnements avec une
adresse ordinaire fictive et un client distant ; voir [parité](ENVIRONMENT_PARITY.md).
**État :** règle actuelle, à maintenir dans chaque nouveau parcours.

## F02 — Un test peut consacrer un mauvais contrat

**Exemple :** [premier commit de #63](https://github.com/eures-beta/match-europe/commit/1f09ec2b8e37eae90e3b2a5eb856d80ff1d78224)
testant la fermeture hors démonstration et pour les clients distants.

**Attendu :** confronter l'attente du test à la décision produit actuelle.
Un ancien test réussi ne justifie pas de conserver une restriction remplacée.
Une maquette explicitement demandée n'est pas une fonctionnalité achevée.

**Contrôle :** vérifier le comportement métier réellement attendu, pas seulement
la présence d'une page ou le succès d'un scénario de démonstration.
**État :** méthode de revue à appliquer, sans réintroduire l'ancien contrat.

## F03 — Une page, un template, gettext

**Exemple :** #63 créait initialement `candidate/fr.html`, `en.html`, `de.html`
et un générateur de copies ; même [commit initial](https://github.com/eures-beta/match-europe/commit/1f09ec2b8e37eae90e3b2a5eb856d80ff1d78224).

**Attendu :** structure commune, gettext FR/EN/DE pour tous les messages visibles.
Ne pas remplacer gettext par un dictionnaire trilingue ou générer trois structures.

**Contrôle :** extraction, vérification et compilation des catalogues, plus rendu
des trois langues. **État :** corrigé pour la landing ; principe durable.

## F04 — Domaine, outils et commandes lisibles

**Exemple :** [premier commit de #76](https://github.com/eures-beta/match-europe/commit/66e4d428de44a8d3c5e63b9f854e3ce4adc4e34f)
ajoutait `scripts/esco/` à la racine, déplacé ensuite dans occupations.

**Attendu :** outil dans le domaine concerné, point d'entrée Make réutilisable ;
pas de nouveau `scripts/` racine, longues recettes répétées dans Markdown ou
cible de test par sous-ensemble. La couche web ne devient pas un domaine métier.

**Contrôle :** rangement, `make help`, commande documentée effectivement exécutée.
**État :** conventions existantes, à appliquer aussi aux nouveaux fichiers.

## F05 — Formatage et séparation des ressources

**Exemples :** JavaScript compact de [#81](https://github.com/eures-beta/match-europe/pull/81),
puis CSS embarqué externalisé dans [#211](https://github.com/eures-beta/match-europe/pull/211).

**Attendu :** sources lisibles, gettext intact, CSS web externe, réutilisation des
composants/tokens. Black n'est pas un formatter HTML/JavaScript/CSS.

**Contrôle :** Black, djLint, Prettier et règles de séparation via les cibles Make.
Un formatter peut laisser une ligne longue ; examiner le résultat plutôt que
présumer que la CI couvre tous les problèmes de lisibilité.
**État :** contrôles en place ; limites à améliorer seulement sur un cas reproduit.

## F06 — Nommer la fonction actuelle, documenter la compatibilité

**Exemple :** `PreviewPushSubscription` et anciens noms Push de
[#192](https://github.com/eures-beta/match-europe/pull/192), puis nettoyage
[#216](https://github.com/eures-beta/match-europe/pull/216).

**Attendu :** le nom décrit la fonction, sans suggérer une restriction de recette
qui n'existe plus. Un renommage ne casse ni données ni contrats cryptographiques.
Une constante dérivant une clé n'est pas un simple texte d'interface.

**Contrôle :** migrations sur données non vides, imports et relations, compatibilité
des liens/clés/abonnements. **État :** corrections en revue, vérifier leurs PR.
