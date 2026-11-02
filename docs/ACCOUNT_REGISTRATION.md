# Création de comptes fermée au public

Les comptes conseiller et employeur ne peuvent pas être créés depuis le site
public. Il n’y a pas encore de mécanisme d’invitation ni de liste blanche : ces
fonctionnalités seront ajoutées dans des PR distinctes.

## Points d’entrée vérifiés

| Point d’entrée | Comportement |
| --- | --- |
| `/employer/access/` | Demande un lien uniquement pour un employeur existant et actif ; ne crée aucun compte. |
| `/employer/confirm/<token>/` | Connecte ce compte existant, sans `get_or_create`. Un ancien lien, ou un lien dont le compte a été supprimé, ne peut pas créer de compte. |
| `/employer/test-inbox/` | Affiche seulement le message simulé de la session ; reste limité au test local existant. |
| Formulaires d’import URL/PDF/texte | Créent éventuellement un brouillon d’offre, jamais un utilisateur. Une adresse de contact n’est pas une identité authentifiée. |
| `/signup/`, `/register/`, `/accounts/signup/`, `/users/signup/` | Aucune route d’inscription ; réponse 404. |
| Administration Django : ajout d’utilisateur | Réservé aux administrateurs habilités ; aucun accès anonyme ou compte ordinaire. |
| Commandes de gestion et migrations | Opérations internes explicites ; ne constituent pas une inscription publique. |

Les restrictions existantes du parcours de connexion employeur (mode d’essai et
accès local) restent appliquées. La réponse à une demande de lien ne distingue
pas publiquement une adresse inconnue d’une adresse existante. Aucun jeton ou
message simulé n’est produit pour une adresse inconnue, un conseiller ou un
compte désactivé. Un ancien message simulé de la session est retiré lors d’une
nouvelle demande acceptée, même si la nouvelle adresse est inconnue.

Les comptes préparés manuellement par une personne habilitée peuvent continuer
à se connecter dans les conditions existantes. Les rôles et privilèges ne sont
jamais choisis à partir des champs soumis au formulaire de connexion.
La création de comptes depuis l’administration reste une action interne
contrôlée, pas une invitation ni une inscription autonome.

## Vérifier

Depuis la racine :

```bash
make registration-test
make test
```

Les tests couvrent les appels HTTP directs, les anciens liens, les comptes
supprimés/désactivés, les deux rôles, la connexion d’un compte existant et
l’absence de création de compte lors d’un import anonyme. Ils vérifient aussi
que les routes d’administration sont inaccessibles aux visiteurs et aux comptes
ordinaires. Aucun e-mail réel n’est envoyé.
