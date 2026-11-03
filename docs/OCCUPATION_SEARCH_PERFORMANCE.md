# Recherche de métiers : éviter le blocage des intitulés mal formés

## Diagnostic

Les journaux de production du 3 novembre 2026 montrent des recherches
`POST /api/occupations/` commencées avant deux `WORKER TIMEOUT` successifs.
Cette route cherche des descriptions de métiers pour l’offre employeur ; le
catalogue est également partagé avec le parcours candidat. Elle reçoit un
intitulé, une langue, un mode et éventuellement le contexte de l’offre.
Les valeurs de ces champs ne sont pas journalisées : l’intitulé exact ayant
déclenché l’incident n’est donc pas connu.

Le défaut reproduit se trouve dans `occupations/catalog.py`, `search_title`.
Le nettoyage des annotations H/F utilisait des quantificateurs imbriqués :
une parenthèse incomplète ou contenant une lettre inattendue peut provoquer
un retour arrière exponentiel. Le problème apparaît sur un intitulé court,
donc la limite de 150 caractères de l’API ne suffit pas à le prévenir.

Ce calcul se déroule en Python, sans SQL ni recherche réseau. La regex peut
monopoliser le GIL du processus : ajouter des threads ne garantit pas que les
autres requêtes ou le mécanisme de surveillance du worker puissent progresser.
Cela constitue une explication compatible avec les symptômes observés, sans
prouver que l’incident de production avait exactement cet intitulé.

## Correction et conservation des résultats

Un passage sans quantificateurs imbriqués reconnaît les parenthèses candidates,
puis une vérification explicite conserve la grammaire historique des annotations.
Les textes ordinaires entre parenthèses restent dans la recherche. L’intitulé
enregistré dans l’offre n’est jamais réécrit. Les classements ESCO/ROME, les
correspondances et le catalogue ne changent pas. Aucun cache de requêtes ou
contexte utilisateur n’est ajouté.

## Mesures locales et tests

`make occupations-benchmark` utilise des intitulés synthétiques, sans réseau,
dans des processus distincts avec une limite de cinq secondes chacun.
Exemples mesurés sur la même machine, à titre indicatif :

| Lettres dans une parenthèse incomplète | Nettoyage avant | Nettoyage après |
| --- | ---: | ---: |
| 20 | 26 ms | 0,20 ms |
| 24 | 480 ms | 0,21 ms |
| 32 | Plus de 5 secondes, processus interrompu | 0,19 ms |

Sur le cas à 32 lettres, la recherche ESCO + ROME après nettoyage termine
environ en 0,35 seconde à froid après correction. Ces mesures locales ne sont
pas une garantie de latence sur une Pico Clever.

`make occupations-performance-test` protège le testeur avec un sous-processus :
un timeout de thread ne suffirait pas face à une regex gardant le GIL. Ce test
échoue sur le premier commit de la PR puis passe après le correctif. Il couvre
parenthèse absente, caractère invalide, espaces répétés, grammaire normale et
route HTTP FR/EN/DE. `make test` couvre aussi les recherches métier existantes.

Aucune migration, aucune donnée nouvelle, aucun changement de droits d’accès.
Si des blocages persistent, profiler séparément le chargement concurrent des
catalogues et les recherches approximatives ; ce correctif ne prétend pas
expliquer tous les problèmes de ressources d’une instance.
