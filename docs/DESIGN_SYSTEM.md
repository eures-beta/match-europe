# Design system Match Europe

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
   européenne, utilisé par eures.europa.eu. Il fournit nos couleurs, la police, les tailles, les
   espacements et la forme des boutons. Documentation : https://ec.europa.eu/component-library/eu/
3. **Bootstrap 5.3** : la base technique des composants (`AGENTS.md`, sections 10 et 18). On ne le
   remplace pas : on l’habille avec les valeurs de l’ECL.
4. **Compléments Match Europe** : ce que l’ECL et Bootstrap ne couvrent pas, ajouté par Yash dans
   ce document.

Pourquoi l’ECL : sa typographie et sa palette sont acceptées par tous les États membres. Elles
évitent un conflit entre les chartes de France Travail, du Forem et de l’ADEM.

## Fichiers

| Fichier                                               | Rôle                                                                   |
| ----------------------------------------------------- | ---------------------------------------------------------------------- |
| `eures_beta/static/design-system/tokens.css`          | Toutes les valeurs (tokens). Seul fichier où un code couleur est écrit |
| `eures_beta/static/design-system/bootstrap-theme.css` | Bootstrap habillé avec les tokens                                      |
| `eures_beta/test_design_system.py`                    | Vérifie automatiquement les règles des tokens                          |
| `/design-system/` (`templates/design_system.html`)    | Page de référence : tokens, contrastes et composants rendus            |

La page `/design-system/` lit `tokens.css` à chaque affichage : elle montre toujours les valeurs
réelles, avec le contraste mesuré de chaque couleur. C’est un outil interne de l’équipe, en
français seulement, et non une fonctionnalité métier. Elle n’est servie qu’en mode démonstration
(`require_demo_access`) : en local avec `ME_DEMO_MODE=1` et `ME_EMPLOYER_DEV_ACCESS=1`, ou sur
une recette partagée en HTTPS. En production, elle répond 404.

Pour une page qui utilise Bootstrap, charger les trois feuilles dans cet ordre :

```django
<link rel="stylesheet" href="{% static 'vendor/bootstrap/bootstrap.min.css' %}">
<link rel="stylesheet" href="{% static 'design-system/tokens.css' %}">
<link rel="stylesheet" href="{% static 'design-system/bootstrap-theme.css' %}">
```

Les écrans existants (`employer/site.css`, `candidate/candidate.css`…) ne sont pas encore migrés.
Ils seront repris écran par écran, en petites PR. **Ne pas copier leurs valeurs** : elles datent
d’avant le design system (ancien bleu `#004494`, police Georgia, une vingtaine d’arrondis).

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

- Police unique : **Arial** (`--me-font-family`), comme sur tous les sites Europa. Pas de Georgia,
  pas de Marianne (police de l’État français, hors sujet pour un service commun à trois pays).
- Titres : token à part, `--me-font-family-heading`, égal à Arial pour l’instant. Une police serif
  pour les titres (Gelasio ou Playfair Display, libres sous licence OFL) est à l’essai sur
  `/design-system/exemple/` ; la décision revient à l’équipe et à Eric. Ne pas utiliser ces
  polices ailleurs avant cette décision.
- Tailles : `--me-font-size-s` (14 px) à `--me-font-size-5xl` (42 px). Le texte courant et les
  champs sont en `--me-font-size-m` (16 px) : en dessous, iOS zoome sur le champ.
  `--me-font-size-xs` (12 px) est réservé aux mentions légales.
- Hauteurs de ligne : le token `--me-line-height-*` de même taille.

### Espacements, formes, contrôles

- Espacements : `--me-space-2xs` (4 px) à `--me-space-4xl` (64 px).
- Arrondis : `--me-radius-m` (4 px) pour les boutons et les champs, `--me-radius-l` (8 px) pour
  les cartes et les panneaux, `--me-radius-round` pour les avatars. **Pas de bouton en pilule.**
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

Composants Match Europe (includes Django) : aucun pour l’instant. Ils arriveront dans
`eures_beta/templates/components/`, et chacun sera ajouté à la page `/design-system/`.

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

`make test` lance `eures_beta/test_design_system.py`. Il échoue si :

- un code couleur apparaît dans `design-system/` ailleurs que dans la palette de `tokens.css` ;
- un fichier utilise un token `--me-*` qui n’existe pas ;
- une valeur R, G, B ne correspond plus à sa couleur.

Le test ne contrôle pas encore les templates ni les anciennes feuilles. Le rendu se vérifie à
l’œil, et le contraste se mesure pour toute nouvelle paire de couleurs.
