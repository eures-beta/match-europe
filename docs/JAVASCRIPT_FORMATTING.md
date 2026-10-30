# Format du JavaScript

Prettier formate les sources JavaScript du projet, avec une indentation de deux
espaces et une largeur cible de 100 caractères. Les chaînes indivisibles peuvent
dépasser cette largeur. Black reste réservé à Python et djLint aux templates.

Installer Node.js 24 LTS, puis lancer `make install-js` et `make format-js`.
`make format-js-check` contrôle le format sans modification et `make check-js`
vérifie la syntaxe. Le workflow GitHub « Format JavaScript » exécute ces deux
contrôles à chaque push et pull request, sans modifier les sources.

La version de Prettier est verrouillée dans les fichiers npm. Aucun bundler ni
build frontend n’est ajouté : les navigateurs utilisent toujours les fichiers
statiques Django. L’extension Prettier de l’éditeur peut utiliser cette même
configuration pour formater à l’enregistrement.
