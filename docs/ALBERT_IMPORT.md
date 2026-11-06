# Essai local de structuration des offres avec Albert

Périmètre employeur, désactivé par défaut : texte d'un PDF (OCR local si nécessaire)
ou annonce collée → structuration Albert → relecture humaine → recherches ESCO et
ROME indépendantes dans les catalogues versionnés. Les imports URL conservent leur
lecteur actuel. Aucun profil candidat, matching ou décision de recrutement par IA.

## Configuration et lancement

Installer les dépendances avec `make install-test` et `make install-js`. Utiliser
une base PostgreSQL distincte et un `.env` personnel ignoré par Git, limité aux
permissions du propriétaire. `ALBERT_API_KEY` est un secret côté serveur : jamais
dans les statiques, les réponses JSON, les journaux, les fixtures ou les commits.
Le secret GitHub ne peut pas être relu pour les essais locaux : utiliser une clé
de développement distincte et révocable.

`ALBERT_IMPORT_ENABLED=1` n'est permis qu'en `DJANGO_ENVIRONMENT=local` ou `preview`,
avec les emails réels désactivés. `ALBERT_MODEL` sélectionne le modèle ; la valeur
initiale est `mistral-small-3-2-24b-instruct-2506`. Ce choix doit encore être comparé
à d'autres modèles sur plusieurs annonces. Les tests automatiques simulent Albert.

Après `make db-create`, `make migrate` et `make test-accounts-seed`, lancer
`make albert-run` et ouvrir le parcours employeur sur le port local 9037.
Le compte employeur fictif se choisit depuis `/accounts/test-accounts/`.
Le lancement active l'essai et le mode de relecture local, sans envoi d'email réel
ni transmission à l'ancien service de préparation. Les destinations et secrets
des recettes jetables restent dans les dépôts privés de déploiement.

## Contrôles et limites

- L'accord de lecture existant est précédé d'une information Albert en FR/EN/DE.
  Seul le contenu fourni est envoyé, pas l'email du compte connecté.
- La clé est envoyée uniquement à l'API officielle, jamais dans une redirection.
- Entrée limitée à 16 000 caractères ; sortie à 100 000 octets et 3 500 jetons.
  Appel avec température zéro, délai réseau de 35 secondes, sans reprise implicite.
- Les textes des champs doivent être des extraits de la source, à espaces
  normalisés. Un champ scalaire non vérifiable reste vide, avec avertissement ;
  les autres champs vérifiés sont conservés. Le texte source est consultable
  pendant la relecture. Ce contrôle ne prouve pas que le modèle a choisi le bon
  passage ou interprété correctement le contrat : la validation humaine reste
  nécessaire. En cas de réponse invalide ou d'indisponibilité, le texte complet
  est proposé pour la saisie manuelle, sans champs locaux devinés.
- Albert ne renvoie aucun code métier utilisé par l'application. Le métier central
  sert de requête initiale ; modifier l'intitulé annule cette requête extraite.
  ESCO et ROME sont recherchés séparément, sans conversion par table d'équivalence.
  Le contexte départage les candidats lexicaux ROME ; il ne sélectionne rien. Une spécialisation sans alias ESCO exact peut proposer le métier plus large explicitement nommé, sans modifier le titre de l’offre.
  Le catalogue ROME et ses appellations restent en français, comme avant cet essai.
- Les droits employeur, la CSRF, le propriétaire et la durée de validité du jeton
  de source sont conservés. Aucun modèle ni migration ajouté. Le texte source et
  les preuves ajoutés pour la relecture ne sont pas recopiés dans l'offre lors de
  l'enregistrement des champs corrigés ; le fonctionnement des sessions existantes
  ne constitue pas une purge automatique du contenu temporaire.
- L'OCR est encore local : aucun envoi direct des images ou PDF à l'OCR Albert.
  La réception d'un PDF ne constitue pas une instruction à exécuter par le modèle.

## Évaluation

`make albert-test` vérifie le contrat de sortie, la confidentialité, les droits,
le repli et le classement ROME, sans réseau. `make occupations-ui-test` vérifie la
requête initiale et son abandon lors d'une correction humaine. Compléter par
`make test`, `make check`, `make check-js`, `make format-check`,
`make format-html-check`, `make format-js-check` et `make translations-check`.

Un appel réel explicite se fait avec `make albert-evaluate ALBERT_INPUT=<chemin>`.
Le fichier peut être un texte UTF-8 ou un PDF ; `ALBERT_OUTPUT` choisit le rapport
local privé. Cette commande transmet le texte à Albert et consomme le quota de
la clé, sans créer d'offre. Ne pas committer les documents ou rapports réels.

Pour la recette manuelle : importer un document, vérifier entreprise/lieu/contrat,
missions/profil et spécialisation, comparer au texte source, puis examiner ESCO et
ROME sans confondre leurs correspondances. Tester aussi un lieu absent, une offre
ambiguë, une erreur du service et une modification du métier. L'enregistrement
requiert toujours les champs et validations métier existants.

## État du 6 novembre 2026

Essai réel local sur une annonce de maintenance de ponts roulants : entreprise,
CDI, expérience de deux ans et absence de lieu correctement restitués ; premières
propositions ESCO 7412.3 et ROME I1304 après prise en compte du contexte. Des
reformulations de la spécialisation ont montré la nécessité de laisser les champs
non vérifiables vides sans perdre toute la réponse. Ce résultat sur un document
ne valide pas la qualité générale du modèle ni ses temps de réponse en production.

Le défaut préexistant du test de bouton a été corrigé à la demande d'Eric : le
tableau de bord conserve son libellé d'import, la page publique son libellé de
besoin de recrutement, et le test vérifie les deux destinations en FR/EN/DE,
avec et sans offres. Aucun libellé d'interface n'a été modifié. La suite complète
a ensuite passé ses 436 tests sur PostgreSQL.

Eric a autorisé la publication après les essais locaux. La PR Albert est empilée
sur la PR #144 ; le bouton partagé et son test déjà harmonisés dans cette base
sont conservés. Aucun passage en production ni fusion n'est inclus.
