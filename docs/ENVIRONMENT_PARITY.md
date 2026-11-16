# Parité fonctionnelle des environnements

## Contrat actuel

Les fonctionnalités métier fonctionnent en local, recette et production avec les
mêmes contrôles de rôle, de propriété, de CSRF, de consentement et de validité.
Leur accès ne dépend pas d'une IP locale, d'un mode démo, d'une adresse fictive
ou de la désactivation des e-mails. L'autorisation d'un agent à déployer ne
conditionne pas le code qu'il livre.

Ce contrat remplace les anciens parcours de prototype local et leurs restrictions,
notamment dans les [PR #154](https://github.com/eures-beta/match-europe/pull/154),
[#157](https://github.com/eures-beta/match-europe/pull/157) et
[#158](https://github.com/eures-beta/match-europe/pull/158).
Les versions et validations historiques restent dans Git et les PR.
Voir [la décision D01](DECISIONS.md#d01--parité-des-environnements).

## Configuration et simulations

- Albert exige une clé privée et le modèle configuré ; `ALBERT_SIMULATED` est
  explicite, désactivé par défaut et commun aux usages. Aucun interrupteur par
  parcours ni simulation automatique selon le nom de l'environnement.
- Les sources ESCO officielles sont préparées avant la requête utilisateur :
  `make continuous-source-prepare`, puis `make skills-source-check`.
  Une absence donne un état explicite, jamais des références inventées.
- Les e-mails passent par le backend Django commun. `EMAIL_DELIVERY_ENABLED=1`,
  le transport SMTP et l'origine de confiance permettent l'envoi dans chaque
  environnement ; l'ancien verrou « production déclarée » est supprimé.
- Les replis guidés/manuels prévus restent disponibles en cas d'indisponibilité
  externe ; ils ne doivent pas prétendre avoir exécuté un service réel.

Les secrets, transports et origines de chaque environnement restent dans les
dépôts/configurations privés. Ces réglages n'octroient aucun droit métier.

## Exception : les données de démonstration

`DEMO_ACCOUNTS_ENABLED` active les comptes et scénarios fictifs uniquement dans
une base fictive local/recette, sans e-mails réels. Le jeu préparé est le même
dans les deux environnements. La création des comptes de démonstration et leur
connexion instantanée sont interdites en production ; les conserver protégées
ne contredit pas la parité des parcours métier.
Voir [les protections](TEST_ACCOUNTS.md) et les [retours F01/F02](AGENT_FEEDBACK.md).

Les anciennes variables `ME_DEMO_MODE`, `ME_SHARED_DEMO`,
`ME_EMPLOYER_DEV_ACCESS`, `ME_EMPLOYER_EMAIL_LOCAL`, `ME_LOCAL_REVIEW_ONLY`
et l'ancien `TEST_ACCOUNTS_ENABLED` ne sont plus lus par l'application.
Les supprimer des configurations privées lors de leur maintenance, sans recopier
de secret ici. Un ancien nom présent n'est pas une deuxième option active.

## Vérification

`make test` couvre configuration et parcours dans les trois environnements avec
clients distants et adresses ordinaires fictives, mêmes opérations et refus.
Les services externes sont simulés ; cela ne prouve pas leur disponibilité réelle
ni l'état d'un déploiement. Consulter les résultats de CI du SHA concerné.

Compléter selon la modification par `make check`, qualité Python/HTML/JS/CSS,
gettext et `make e2e-test`. Un compteur de tests ancien ne vaut pas validation
du code courant ; ne pas entretenir une chronologie de compteurs dans ce guide.
