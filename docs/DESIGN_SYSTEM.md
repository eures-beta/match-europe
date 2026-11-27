# Design system EURES — Match Europe

Ce document dit comment construire une interface Match Europe. Il s’adresse aux personnes de
l’équipe et à leurs agents IA. Un agent qui crée ou modifie un écran le lit avant d’écrire du HTML
ou du CSS.

Responsable : Yash (harmonisation UI, compte rendu d’équipe du 13 novembre 2026). Une question ou
un composant manquant se signale à Yash avant d’inventer une solution.

## Sources et ordre de priorité

1. **EURES Graphic Guidelines 2022** (`AGENTS.md`, section 11) : logo EURES, zone de protection,
   co-branding. Ce PDF n’est pas encore dans le dépôt. Tant qu’il manque, ne pas toucher au logo
   EURES ni à l’en-tête de marque.
2. **Europa Component Library (ECL) v5.4.1, déclinaison EU** : le design system de la Commission
   européenne, utilisé par eures.europa.eu. Il fournit nos couleurs, la police du texte, les
   tailles et les espacements. Documentation : https://ec.europa.eu/component-library/eu/
3. **Bootstrap 5.3** : la base technique des composants (`AGENTS.md`, sections 10 et 18). On ne le
   remplace pas : on l’habille avec les valeurs de l’ECL.
4. **Compléments Match Europe** : ce que l’ECL et Bootstrap ne couvrent pas, ajouté par Yash dans
   ce document.

Pourquoi l’ECL : sa typographie et sa palette sont acceptées par tous les États membres. Elles
évitent un conflit entre les chartes de France Travail, du Forem et de l’ADEM.

## Fichiers

Les styles des pages web restent dans des feuilles CSS séparées : voir la
[politique HTML/CSS](HTML_CSS.md). Les styles historiques externalisés conservent
leurs valeurs pendant cette migration de rangement ; tout nouveau composant
continue d'utiliser les tokens et composants décrits ici.

| Fichier                                               | Rôle                                                                    |
| ----------------------------------------------------- | ----------------------------------------------------------------------- |
| `eures_beta/static/design-system/tokens.css`          | Toutes les valeurs (tokens). Seul fichier où un code couleur est écrit  |
| `eures_beta/static/design-system/bootstrap-theme.css` | Bootstrap habillé avec les tokens                                       |
| `eures_beta/static/design-system/components.css`      | En-tête, pied de page et composants `ds-*` des pages réelles |
| `eures_beta/static/design-system/demo.css`            | Mise en page de la seule page de référence graphique |
| `eures_beta/templates/eures_base.html`                | Gabarit des pages de production passées au design system                |
| `eures_beta/static/design-system/fonts/`              | Police Gelasio et sa licence, chargées par `tokens.css`                 |
| `tests/common/test_design_system.py`                  | Vérifie automatiquement les règles des tokens                           |
| `/design-system/` (`templates/design_system.html`)    | Page de référence : tokens, contrastes et composants rendus             |

La page `/design-system/` lit `tokens.css` à chaque affichage : elle montre toujours les valeurs
réelles, avec le contraste mesuré de chaque couleur. Ce catalogue public est une unique
page de référence graphique (« cookbook »), sans connexion ni droit staff dans aucun environnement.
Le pied de page commun la relie au projet, au journal, à la protection des données et
à l’organisation GitHub publique EURES Beta ; ces liens sont traduits en FR/EN/DE.
Ses boutons et champs illustrent des composants ; ils ne simulent pas un parcours métier et
ne sauvegardent aucune donnée. Les anciennes pages factices et leurs routes ont été supprimées.

Une page de production passée au design system étend `eures_base.html` : il charge les quatre
feuilles, l’en-tête réel (langues, compte, logos, navigation) et le pied de page. Pour une page qui
utilise Bootstrap sans ce gabarit, charger les feuilles dans cet ordre :

```django
<link rel="stylesheet" href="{% static 'vendor/bootstrap/bootstrap.min.css' %}">
<link rel="stylesheet" href="{% static 'design-system/tokens.css' %}">
<link rel="stylesheet" href="{% static 'design-system/bootstrap-theme.css' %}">
<link rel="stylesheet" href="{% static 'design-system/components.css' %}">
```

Les écrans existants (`employer/site.css`, `candidate/candidate.css`…) passent au design system
dans une seule PR, pour ne jamais livrer deux designs en même temps. Déjà passé : accueil employeur, espace employeur (offres, fiche, modification), confidentialité employeur.
Les formulaires Django y reçoivent leurs classes Bootstrap par `www/design_system.py` et
`templates/eures/form_field.html`. **Ne pas copier leurs valeurs** : elles datent
d’avant le design system (ancien bleu `#004494`, police Georgia, une vingtaine d’arrondis).

## Direction visuelle : hybride

Décidée le 13 novembre 2026 (Eric, PO) parmi trois propositions : **EURES strict**, **continuité**
(l’esprit des anciens écrans) et **hybride**. L’hybride garde la base commune EURES (Arial pour le
texte, couleurs et statuts ECL, composants) et y ajoute la personnalité de Match Europe : titres
en serif (Gelasio), arrondis moyens, ombres discrètes et fond de page bleu très pâle.

La page `/design-system/` montre les composants isolément : elle ne prétend être ni une offre,
ni un tableau de bord, ni une page de connexion. Les vrais parcours restent dans leurs templates métier.

## Tokens

Deux niveaux :

- **Palette** (`--me-palette-*`) : les valeurs de l’ECL, copiées telles quelles. Ne jamais les
  utiliser directement dans une page.
- **Rôles** (tous les autres `--me-*`) : ce que les pages et les composants utilisent. Un rôle dit
  à quoi sert la couleur, pas de quelle couleur il s’agit.

### Couleurs

| Token                       | Usage                                            | Contraste sur blanc |
| --------------------------- | ------------------------------------------------ | ------------------- |
| `--me-color-text`           | Texte courant                                    | 16,9:1              |
| `--me-color-text-muted`     | Texte secondaire, aides de champ                 | 7,5:1               |
| `--me-color-link`           | Liens                                            | 7,6:1               |
| `--me-color-action`         | Fond des boutons principaux                      | 7,6:1               |
| `--me-color-accent`         | Jaune UE : décoration seulement, jamais du texte | —                   |
| `--me-color-surface`        | Fond de page et de carte                         | —                   |
| `--me-color-surface-subtle` | Fond de section secondaire                       | —                   |
| `--me-color-surface-brand`  | Fond bleu très clair (encart, survol)            | —                   |
| `--me-color-border`         | Séparateurs décoratifs                           | —                   |
| `--me-color-border-strong`  | Bordure des champs de formulaire                 | 7,5:1               |
| `--me-color-focus`          | Contour de focus clavier                         | 7,6:1               |
| `--me-color-error`          | Erreur : texte, bordure, icône                   | 5,3:1               |
| `--me-color-success`        | Succès : bordure et icône seulement              | 3,3:1               |
| `--me-color-warning`        | Avertissement : bordure et icône seulement       | 2,5:1               |

Le vert et l’orange de l’ECL n’atteignent pas le contraste WCAG AA pour du texte. Dans une alerte
de succès ou d’avertissement, le message s’écrit en `--me-color-text`, sur le fond
`--me-color-*-surface`, avec la couleur de statut en bordure ou en icône.

Une couleur signale toujours la même chose. Ne jamais transmettre une information par la couleur
seule : ajouter un texte ou une icône.

### Typographie

- Texte : **Arial** (`--me-font-family`), comme sur tous les sites Europa. Pas de Marianne
  (police de l’État français, hors sujet pour un service commun à trois pays).
- Titres (`h1` à `h6`, classes `.h1` à `.h6`) : **Gelasio** (`--me-font-family-heading`), serif
  libre sous licence OFL (fonderie Sorkin Type), servie par Match Europe depuis
  `design-system/fonts/`, sans appel à Google. Repli : Georgia. Choix de Yash, susceptible d’évoluer :
  changer la police des titres ne demande que ce token. Ne pas l’utiliser pour le texte courant.
- Tailles : `--me-font-size-s` (14 px) à `--me-font-size-5xl` (42 px). Le texte courant et les
  champs sont en `--me-font-size-m` (16 px) : en dessous, iOS zoome sur le champ.
  `--me-font-size-xs` (12 px) est réservé aux mentions légales.
- Hauteurs de ligne : le token `--me-line-height-*` de même taille.

### Espacements, formes, contrôles

- Espacements : `--me-space-2xs` (4 px) à `--me-space-4xl` (64 px).
- Arrondis : les composants lisent les tokens d’usage, jamais l’échelle directement.
  `--me-radius-control` pour les boutons et les champs (8 px), `--me-radius-card` pour les cartes,
  panneaux et alertes (12 px), `--me-radius-badge` pour les étiquettes (8 px), `--me-radius-round`
  pour les avatars. **Pas de bouton en pilule.**
- Ombre des cartes : `--me-shadow-card`, légère. Fond de page : `--me-page-background`.
- Hauteur minimale d’un bouton ou d’un champ : `--me-control-min-height` (48 px).
- Focus : contour plein de 2 px (`--me-focus-outline-width`), jamais supprimé.

## Composants

Toujours dans cet ordre :

1. **Un composant Match Europe existe** (liste ci-dessous) : le réutiliser tel quel.
2. **Bootstrap le fournit** : utiliser la classe Bootstrap. Le thème lui donne l’apparence ECL.
3. **Rien n’existe** : voir « Créer un composant ».

| Besoin                | À utiliser                                             | Équivalent ECL |
| --------------------- | ------------------------------------------------------ | -------------- |
| Action principale     | `btn btn-primary`                                      | Primary        |
| Action secondaire     | `btn btn-outline-primary`                              | Secondary      |
| Action discrète, lien | `btn btn-link`                                         | Tertiary       |
| Champ texte, liste    | `form-control`, `form-select`                          | Text field     |
| Case, bouton radio    | `form-check-input`                                     | Checkbox       |
| Libellé, aide, erreur | `form-label`, `form-text`, `invalid-feedback`          | —              |
| Message de statut     | `alert alert-success` (`-warning`, `-danger`, `-info`) | Notification   |

Une seule action principale par écran ou par bloc. Ne pas utiliser `btn-secondary`, `btn-warning`
ni les autres variantes de couleur de Bootstrap pour des boutons : elles n’ont pas d’équivalent ECL.

### Compteurs d’actions conseiller

Les menus « À traiter » utilisent `.adviser-action-count` dans
`static/adviser/action-queue.css` : petit badge rouge (`--me-color-error`), texte
inversé, arrondi de badge et libellé accessible donnant le nombre d’actions.
Il est masqué à zéro et ne compte pas les recherches reportées à une date future.

### Fiches conseiller

Le dialogue privé candidat utilise la palette commune dans
`matching/static/matching/candidate-conversation.css`. Avant cet étage de la pile,
ces styles restent autonomes ; le raccordement aux tokens et leur chargement
commun sont livrés ensemble ici. Sur ordinateur, un cadre de téléphone
contient le défilement ; sur mobile, le dialogue occupe la largeur disponible.
Le suivi conseiller conserve son tableau sémantique et son panneau email distincts
dans `adviser/conversation-followup.css`.

Les fiches offre/candidat de « À traiter » utilisent `adviser/record-detail.css` :
résumé en tête, sections thématiques, libellés discrets et contenu lisible, suivi
séparé dans un panneau latéral sur ordinateur. Sur petit écran, les blocs s’empilent ;
les liens de rubrique donnent aussi accès au suivi. Couleurs et mesures viennent des tokens.

### En-tête et liens de navigation

Les pages utilisant `eures_base.html` partagent le même en-tête : logo et
nom Match Europe, menu de langue, liens du compte, puis la bande des logos partenaires
(`eures/partners.html`). Sur téléphone, l’accroche est masquée, les quatre logos tiennent
sur une ligne et la navigation principale défile de côté.

- **Soulignement** : un lien dans un texte reste souligné (règle ECL, accessibilité). Un élément de
  menu, de navigation ou d’en-tête n’est pas souligné, sauf au survol.
- **Langue** : un bouton « FR » ouvre la liste Français, English, Deutsch (`details`, sans
  JavaScript). La langue active est marquée par un fond bleu pâle, du gras et une coche.
- **Déconnexion** : action secondaire, en gris (`ds-logout`).
- **Logos partenaires** : fichiers de production, non modifiés. Chaque fichier a ses propres
  marges : chaque logo a donc sa largeur en `rem`, faute de token de taille de logo.

Les fragments Django partagés sont dans `templates/eures/` (logos, formulaires, statut d’offre)
et `templates/includes/useful_links.html` (pied de page public). Réutiliser ces fragments
plutôt que recréer un en-tête ou des liens propres à chaque parcours.

## Créer un composant

1. Chercher d’abord par le libellé visible : templates, `templates/includes/`, puis Bootstrap. Ne
   pas créer une variante d’un composant existant pour le même usage.
2. Partir d’un composant Bootstrap, et le rapprocher de l’ECL s’il y a un équivalent.
3. N’utiliser que des tokens `--me-*` de rôle. Aucune valeur brute (couleur, taille, arrondi). Si
   un token manque, le proposer dans la PR plutôt que d’écrire la valeur.
4. Vérifier : clavier, focus visible, libellés, contraste AA, mobile, textes traduits (FR, EN, DE).
5. Ajouter le composant à la liste de ce document dans la même PR, et prévenir Yash en relecture.

## Ce qu’un agent ne fait pas

- Écrire un code couleur, une police ou une taille en dur dans un template ou un CSS.
- Utiliser un token `--me-palette-*` directement.
- Modifier `tokens.css` sans le signaler dans la PR : c’est un changement de charte
  (`AGENTS.md`, section 17).
- Modifier le logo EURES, sa zone de protection ou une couleur officielle.
- Ajouter une bibliothèque CSS, une police web ou une icône externe.
- Reprendre les valeurs des anciennes feuilles (`site.css` et voisines).

## Vérification

Le gabarit EURES conserve le bandeau commun des comptes fictifs et sa feuille CSS
uniquement lorsque ces comptes sont autorisés. Les tests de pages vérifient une
seule bannière en FR/EN/DE en recette et son absence, avec celle de sa CSS, en production.

Les e-mails utilisent [un gabarit commun](EMAIL_LINKS.md#présentation-partagée)
reprenant la présentation des invitations employeur. Leurs styles intégrés et
logos existants sont isolés dans `templates/emails/`, sans Bootstrap distant ;
cette contrainte de messagerie ne change pas la politique CSS des pages web.

`make test` lance `tests/common/test_design_system.py`. Il échoue si :

- un code couleur apparaît dans `design-system/` ailleurs que dans la palette de `tokens.css` ;
- un fichier utilise un token `--me-*` qui n’existe pas ;
- une valeur R, G, B ne correspond plus à sa couleur.

Le test ne contrôle pas encore les templates ni les anciennes feuilles. Le rendu se vérifie à
l’œil, et le contraste se mesure pour toute nouvelle paire de couleurs.
