---
name: interface-change
description: Créer ou modifier une interface, un template, un message JavaScript ou un e-mail de Match Europe avec gettext, design system EURES et accessibilité.
---

# Interface et messages

Lire le [design system](../../../docs/DESIGN_SYSTEM.md), les
[règles HTML/CSS](../../../docs/HTML_CSS.md), les [retours](../../../docs/AGENT_FEEDBACK.md)
et le guide du parcours. Réutiliser Bootstrap, tokens ECL et composants existants ;
préserver les EURES Graphic Guidelines 2022 et les assets officiels.

Un template commun, gettext FR/EN/DE pour titres, textes, erreurs, aides et e-mails ;
pas de copies par langue ni de dictionnaire trilingue remplaçant gettext.
Après une nouvelle chaîne : `make translations-extract`, compléter les catalogues,
puis `make translations-check translations-compile`.

CSS web externe via static ; seuls les e-mails HTML et attributs dynamiques du
catalogue design-system ont les exceptions documentées. Ne pas neutraliser le lint
d'une page métier. Appliquer `make format-html-check format-js-check format-css-check check-js`
après formatage avec les cibles correspondantes ; Black traite seulement Python.

Vérifier clavier, focus, labels, sémantique, contrastes, alternatives, responsive
et états d'erreur. Les informations ne reposent pas uniquement sur la couleur.
Tester les trois langues et les comportements JS utiles ; distinguer les tests
automatisés des contrôles visuels ou sur téléphone réellement effectués.

Le même parcours est livré dans tous les environnements. Une clé manquante ou
un envoi désactivé ne justifie pas de transformer le parcours en maquette.
Distinguer clairement une étape non implémentée d'une fonctionnalité terminée.
