# Lire une description de pull request

```bash
make pr-description PR=195
```

Cette commande lit seulement la description GitHub du dépôt Match Europe, puis
affiche le chemin du fichier `.runtime/pr-195-description.md`. Le fichier local
est ignoré par Git et accessible seulement à son propriétaire. GitHub CLI doit
être installé et connecté. Aucun environnement Django ou PostgreSQL n'est requis.

La recette n'interpole pas PR dans une commande shell : le numéro est transmis
comme donnée et doit être un entier positif. La lecture doit réussir et produire
un JSON valide avant publication atomique du fichier. Une description réellement
vide est acceptée ; un échec réseau, GitHub ou de décodage échoue avec un statut
non nul et ne laisse pas l'ancienne description disponible comme résultat frais.

Vérifier le succès de la commande avant toute modification du fichier ou édition
de la PR. Aucun push, commentaire, modification de PR ou déploiement n'est effectué.

```bash
make pr-description-test
```

Les tests sont hors réseau : succès Unicode, paramètres invalides, résultat vide,
réponse invalide et échec réseau avec une ancienne description déjà présente.
Un test appelle aussi Make avec une expression shell dans PR et vérifie qu'elle
n'est jamais exécutée.

Une éventuelle règle locale d'approbation peut être limitée au préfixe
`["make", "pr-description"]`, réutilisable pour les autres numéros. Le dépôt ne
modifie pas les permissions de Codex : chaque client conserve ses contrôles réseau
et fichiers. Le Makefile expose l'opération, il ne contourne pas ces contrôles.
