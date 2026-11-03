# Consulter les données dans Django Admin

Les neuf modèles applicatifs et cinq modèles techniques Django installés sont
enregistrés explicitement. La page `/admin/` permet aux superadministrateurs actifs
avec `is_staff=True` de les consulter, rechercher et filtrer. Les relations restent
navigables lorsque leur modèle autorise la consultation détaillée.

- Employeurs : entreprises, appartenances, imports, vérifications e-mail,
  opérations de recherche et événements.
- Utilisateurs : comptes, invitations employeurs et compteurs anti-abus.
- Django : groupes, permissions, types de contenu, métadonnées des sessions et
  du journal d'administration.

Les autres comptes staff habilités conservent uniquement la consultation des
conseillers. Les nouveaux écrans sont réservés aux superadministrateurs, même
si un autre compte reçoit manuellement une permission Django sur ces modèles.

## Lecture seule

Aucun ajout, modification, suppression, action groupée ou modification de droits
n'est autorisé par ces administrations, y compris pour un superutilisateur.
Les requêtes POST directes sont refusées côté serveur ; cacher les boutons ne
constitue pas la protection. La création administrative de conseillers est retirée
et le groupe versionné `account-admin` ne reçoit plus `users.add_user`.
Le workflow d'invitation des employeurs, hors Django Admin, reste inchangé.

Cela ne transforme pas la connexion PostgreSQL en connexion read-only : sessions
et authentification continuent à fonctionner normalement. Aucun indicateur de
compte existant n'est changé par cette PR ; aucune migration n'est nécessaire.

## Secrets

Les champs mot de passe, clé et contenu de session, empreinte de vérification
e-mail et nonce d'invitation sont exclus des fiches. Les sessions n'ont aucune
fiche détaillée ni lien portant leur clé : seules une référence SHA-256 tronquée
et l'expiration sont visibles. Les entrées du journal n'exposent que date, acteur,
modèle et type d'action, sans les anciens messages ou représentations d'objets.
Le bloc « Actions récentes » et les accès aux anciens historiques détaillés sont
retirés pour la même raison ; la liste des métadonnées du journal reste accessible.

Les JSON d'import, contacts et réponses externes sont formatés et échappés HTML.
Les valeurs structurées sous des clés de secret connues (token, password,
authorization, session, etc.) sont masquées, comme les paramètres de ces noms
dans les URL sources. Cela n'est pas un détecteur universel de secrets dans du
texte libre : les données métier restent visibles aux superadministrateurs.
Les données personnelles ne sont pas rendues publiques et ne sont pas exportées.

## Maintenance et vérification

Chaque modèle est enregistré dans le `admin.py` de son domaine ; la base commune
de lecture seule est dans `users/admin_base.py`. Les modèles Django sont enregistrés
après découverte complète des modules admin pour remplacer l'éditeur de groupes
natif. Aucun modèle futur n'est exposé automatiquement : le test d'exhaustivité
signalera qu'un enregistrement explicite doit être ajouté.

```bash
make admin-test
make test
make check
```

Les tests couvrent les listes et fiches, tous les endpoints de mutation, les
actions forgées, les rôles non autorisés, les secrets et l'échappement HTML.
## Afficher ou masquer les filtres

Un bouton sur les listes avec filtres masque ou réaffiche leur panneau, en
conservant les filtres actifs. Le choix est mémorisé pour les listes de cette
administration dans le navigateur (`localStorage`, un booléen sans donnée métier).
Si le stockage est indisponible, le bouton reste utilisable sur la page courante.
Sans JavaScript, les filtres restent visibles. Aucune modification de la barre
de navigation, des e-mails, des permissions ou du comportement selon la largeur.

Vérifications : `make test` pour les pages et traductions, `make check-js` pour
les interactions et leur mémorisation.
## Nombres d’enregistrements à la demande

Sur l’accueil de l’administration, « Afficher les nombres d’enregistrements »
ajoute un total entre parenthèses à chaque modèle visible, y compris zéro.
Le lien « Masquer » revient à l’affichage habituel. L’activation reste uniquement
dans l’URL (`model_counts=1`), sans cookie, préférence persistante ou nouvelle
donnée en base. Sans ce paramètre exact, aucun comptage supplémentaire.

Chaque nombre est calculé avec le queryset du ModelAdmin et ses permissions :
un administrateur limité aux conseillers voit seulement leur nombre, pas tous
les comptes. Les modèles interdits ne sont pas comptés. Le panneau de navigation
n’est pas enrichi de compteurs. Lorsque l’option est activée, une requête COUNT
par modèle visible est nécessaire ; les résultats ne sont pas mis en cache et
peuvent évoluer entre deux requêtes si des données sont créées en parallèle.

Vérification des droits, des comptes nuls et de l’absence de COUNT par défaut :
`make test`. Les tests utilisent exclusivement PostgreSQL local et des données
fictives.
La navigation gauche est masquée par défaut en l’absence de préférence navigateur.
Le bouton natif Django permet de la rouvrir et mémorise le choix. Un choix déjà
enregistré reste respecté. Le comportement du panneau de filtres à droite reste
inchangé : visible par défaut, avec son propre bouton et sa propre préférence.
