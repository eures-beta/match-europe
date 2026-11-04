# Compte utilisateur unique

`eures_beta.users.User` hérite de `django.contrib.auth.models.AbstractUser`,
comme le modèle `itou.users.User` des Emplois. Django conserve la gestion des
mots de passe, sessions, groupes, permissions et de l’administration.
`AUTH_USER_MODEL` désigne `users.User` ; il n’y a pas de modèle Profile.

L’e-mail remplace le nom d’utilisateur pour la connexion. Le champ obligatoire
`kind` vaut `adviser` (conseiller), `employer` (employeur) ou `candidate`
(candidat). Il n’a pas de valeur
par défaut. `is_staff` et `is_superuser` restent des privilèges techniques, pas
des rôles supplémentaires. Le rôle est immuable après création, dans le modèle
et par un déclencheur PostgreSQL qui protège également les mises à jour directes.
Une contrainte PostgreSQL impose l’unicité de l’e-mail sans distinction de casse.
Le gestionnaire normalise les adresses et crée un mot de passe inutilisable
lorsqu’aucun mot de passe n’est fourni.

## 4 novembre 2026 — socle des comptes candidats

Le premier lot ajoute `candidate` aux choix et à la contrainte PostgreSQL
`users_valid_kind` (migration `users.0005_candidate_kind`). Il conserve le
déclencheur d’immuabilité, l’unicité de l’email et les privilèges techniques
séparés. Le tableau de bord candidat utilise la page générique existante ; il
ne passe pas par l’espace employeur. Les invitations conseillers et les accès
employeurs restent refusés aux candidats.

Ce lot ne crée aucun compte depuis une page publique et ne change pas les
liens de connexion existants. Le futur parcours candidat autorisé par Eric
permettra de remplir le questionnaire sans connexion, puis de créer le compte
en fin de parcours et de vérifier l’adresse par email. Son implémentation est
distincte de la connexion habituelle des comptes existants.

Tester le rôle, les protections et la transition depuis `users.0004` avec
`make user-kind-test`, puis les interactions avec `make test`.
La migration inverse n’est applicable que si aucun compte candidat ne subsiste :
la contrainte précédente refuse cette valeur. Aucun compte n’est supprimé ou
converti automatiquement pour permettre un retour arrière.

## Remplacement d’EmployerIdentity

Les adhésions aux établissements, auteurs d’import, demandes de recherche et
auteurs d’événements pointent désormais vers le même utilisateur Django.
La migration transfère les identités avec leur identifiant et date de création,
sans supprimer les offres ni leurs rattachements. Les collisions d’identifiants
ou d’e-mails ambigus bloquent la transition ; aucune fusion implicite.

La connexion employeur utilise désormais la session Django. Elle refuse les
comptes désactivés et les comptes conseiller sur ce parcours. Les anciennes
sessions contenant seulement `employer_identity_id` ne sont pas reconnues :
une nouvelle connexion est nécessaire. Les restrictions locales et les
conditions de mode fictif existantes restent en place. Cette PR n’active ni
Brevo, ni inscription publique, ni connexion employeur sur Internet.
Les imports anonymes restent rattachés à la session tant qu’ils ne sont pas
revendiqués par un utilisateur autorisé.

## Transition d’une base déjà migrée

Changer `AUTH_USER_MODEL` modifie aussi les dépendances historiques de Django.
La commande `migrate` du paquet `users` étend donc la commande native : lorsque
`users.0001_initial` manque, elle applique réellement cette migration avec
l’ancienne identité `auth.User`, puis reprend les migrations avec `users.User`.
Les modules de migration sont rechargés entre ces deux étapes, car leurs
références configurables sont évaluées à l’import. Aucun `--fake` ni modification
manuelle de `django_migrations`. Les exécutions suivantes ne refont pas ce passage.
Les options de consultation `--plan` et `--check` ne lancent pas la préparation.

Sur une base ayant déjà des tables employeur, la commande exige d'abord le
marqueur `employers.0001_autonomous_schema`. Son absence bloque avant toute
bascule utilisateur ; il faut appliquer la version de transition autonome.

La première étape **refuse tout utilisateur dans l’ancienne table `auth_user`** :
on ne peut pas deviner son rôle. Une base contenant de tels comptes demande
une stratégie d’attribution explicite avant cette transition. Le contrôle est
exécuté dans la migration, pas déduit d’un constat ancien sur un environnement.
Après cette vérification, la table vide et ses jointures sont supprimées ; leurs
clés étrangères restantes sont dirigées vers `users_user`. Les anciennes
permissions de modèle peuvent rester en base, mais ne deviennent pas des
permissions du nouveau modèle par équivalence implicite.

La préparation et le transfert sont des migrations transactionnelles distinctes.
Si le transfert refuse une collision, les identités d’origine restent présentes
et la migration peut être relancée après correction. Le retour avant la création
de `users.User` n’est pas automatique : prévoir une sauvegarde et une restauration
validée avant de déployer ce changement. Un retour de code seul n’annule pas
la transition du schéma.

## Vérifications reproductibles

Depuis la racine :

```bash
make test
make check
make users-upgrade-test
```

La dernière cible crée une base PostgreSQL locale temporaire, reproduit l’ancien
schéma puis teste le passage réel vers le nouveau. Elle vérifie le blocage sans
suppression d’un ancien compte sans rôle, le refus des collisions d’e-mails,
la conservation des quatre relations et du contenu d’offre, puis une seconde
exécution des migrations. La base est supprimée à la fin ; les hôtes distants
sont refusés. Cette cible est également exécutée par la CI avant déploiement.

Les tables d’identité sont verrouillées pendant leur transfert pour éviter une
création concurrente entre vérification et suppression. Ce changement de schéma
est incompatible avec l’ancien code : prévoir une fenêtre de maintenance, et
ne pas faire fonctionner simultanément anciennes et nouvelles instances pendant
la bascule.

## Compatibilité avec la consolidation autonome

La migration utilisateur dépend de `employers.0001_autonomous_schema`, sans
référence aux archives désormais supprimées. `make migrations-test` vérifie le
schéma actuel et la conservation des données lors d'une nouvelle exécution.
Le scénario `make users-upgrade-test` crée réellement le schéma autonome avec
`auth.User`, puis exerce la transition vers `users.User`. Il vérifie aussi le
refus d'une base sans marqueur autonome avant toute création de table utilisateur.
Les contrôles de rôles, collisions d'e-mails et conservation des quatre relations
restent vérifiés dans cette base locale jetable.

La connexion ne crée plus de compte implicitement : seuls les employeurs
existants et actifs sont acceptés. Voir [la fermeture des inscriptions](ACCOUNT_REGISTRATION.md).
