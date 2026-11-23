# Séparer les templates HTML et les feuilles CSS

Les templates web décrivent la structure, le contenu et les classes. Le CSS
vit dans des fichiers statiques, chargés avec `{% static %}`. Réutiliser d'abord
Bootstrap et les composants communs existants.
Partager les règles communes ; un fichier CSS par template n'est pas obligatoire.
Ranger les particularités par parcours, comme `static/adviser/history.css`.

## Chargement et conservation du rendu

Les pages publiques et candidat partagent `public/layout.css` et
`public/header-actions.css`. L'accueil employeur conserve sa variante
`employer/landing-layout.css`. L'import et les écrans d'authentification employeur
partagent `employer/layout.css` et `employer/import-layout.css` ; les compléments
d'authentification sont dans `employer/auth-layout.css`. L'espace employeur charge
`employer/workspace.css` ; l'historique du conseiller utilise `adviser/history.css`.

Les 17 blocs historiques de sept templates ont été externalisés en huit feuilles.
Leurs sélecteurs, valeurs et ordre ont été conservés, y compris les surcharges
volontaires. Seuls des blocs identiques sont partagés, et des blocs adjacents sont
regroupés. Ces règles historiques n'ont pas été redessinées ni converties en
tokens dans ce lot : ne pas copier leurs anciennes valeurs pour un nouveau composant.
Les prochains changements graphiques utilisent les tokens et se relisent séparément.

Une extraction doit conserver la place de la feuille dans la cascade. Vérifier
les éventuels chemins `url(...)` relatifs au nouveau fichier ; ne pas déplacer
automatiquement une expression Django dans une feuille statique.

## Contrôle bloquant existant en CI

Après `make install-quality`, `make format-html-check` exécute le formatage et le
contrôle de structure existants, puis djLint et les tests de la politique CSS :

- H021, règle native djLint : interdit les attributs `style` ;
- C901, règle projet dans [`.djlint_rules.yaml`](../.djlint_rules.yaml) : interdit
  les balises `<style>` dans les pages web.

La configuration [`.djlint-css.json`](../.djlint-css.json) isole ce contrôle :
`--include` dans djLint ajoute des règles et ne sélectionne pas seulement celles
nommées. Les autres règles de lint connues sont donc ignorées dans cette
configuration dédiée, sans toucher au formateur [`.djlintrc`](../.djlintrc) ni
aux contrôles HTML existants. Réviser cette liste lors d'une mise à jour djLint.
Il n'y a ni nouveau formateur, ni extraction automatique pendant la CI.

Le workflow templates utilise déjà `make format-html-check` à chaque push et PR.
Les fichiers CSS passent dans le Prettier existant, avec `make format-css` et
`make format-css-check`. Les sources tierces restent exclues.

## Exceptions explicites

- `invitations/templates/invitations/emails/` : les styles intégrés sont conservés
  pour la compatibilité des clients e-mail.
- `templates/emails/base.html`, `action.html`, `message.html` et `link_fallback.html` :
  composants d'e-mail communs, attributs `style` autorisés mais blocs `<style>` interdits.
  Les autres fichiers de ce dossier ne sont pas automatiquement exemptés.
- `templates/design_system.html` : seuls ses attributs `style` sont autorisés,
  pour représenter les valeurs des tokens lus dynamiquement. Les blocs `<style>`
  restent interdits dans ce catalogue.

Ces exceptions ne s'appliquent pas aux pages métier ni aux fichiers dont le nom
ressemble au catalogue. Ne pas ajouter une exemption locale `djlint:off` ou
élargir la configuration pour éviter d'externaliser un style.

## Tests

`make format-html-check` teste les violations et les exceptions avec le vrai CLI
djLint de l'environnement qualité. Ces tests sont sautés par la suite applicative
si djLint n'y est pas installé : ils restent obligatoires dans le contrôle templates
de CI. Aucune dépendance qualité n'est ajoutée au serveur de production.
`make test` vérifie le chargement des feuilles et leur ordre dans les pages,
notamment l'historique conseiller. `make e2e-test` vérifie les parcours HTTP.

[Retour à la documentation](./)
