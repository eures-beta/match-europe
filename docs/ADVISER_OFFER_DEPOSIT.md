# Déposer une offre pour un employeur

Un conseiller actif ouvre « Mes offres déposées », sélectionne un établissement
existant ou en crée un distinct, puis utilise le même import PDF/URL/texte et la
même relecture que l’employeur. Le dépôt ne crée jamais de compte employeur.

Pour un établissement possédant des membres actifs, le conseiller désigne un
compte contact parmi eux. Pour un nouvel établissement, il peut explicitement
donner accès à un compte employeur existant. Sans compte, il conserve simplement
les coordonnées du contact de l’offre. Aucun rapprochement d’email n’accorde de droit.

## Confirmation et suivi

La confirmation téléphonique suffit : case explicite, date au plus tard aujourd’hui,
champs essentiels complétés. Enregistrement du conseiller, de l’instant de saisie
et de la révision confirmée. Le matching est programmé après commit. Ni email de
validation ni compte employeur ne sont nécessaires. Pas d’envoi AGLAE au dépôt.

Le conseiller retrouve ses dépôts dans son portefeuille ; les conseillers gardent
leur consultation globale de l’historique. Les membres de l’établissement voient
la même offre dans leur compte, avec sa provenance conseiller. Le créateur reste
le conseiller, distinct du compte contact employeur et du propriétaire établissement.

Une nouvelle révision nécessite une nouvelle confirmation pour le matching.
La modification côté conseiller réutilise les validations de l’offre/contact et
contrôle la révision ; elle demande une confirmation téléphonique renouvelée.
Une recherche déjà démarrée conserve le verrouillage existant.

## Reprise par l’employeur

Depuis le détail d’un dépôt sans accès employeur, le conseiller peut préparer une
invitation liée explicitement à l’établissement. L’acceptation sécurisée crée le
compte et l’adhésion, rend visibles les offres existantes et désigne le contact
des dépôts qui n’en ont pas encore. Aucune récupération automatique par email.
La conversation à trois nécessite toujours un compte employeur actif et membre ;
son absence n’empêche pas le dépôt et le calcul de matching.

## Stockage et validation

Migrations additives `employers.0009` et `invitations.0004`, anciennes lignes
conservées avec valeurs nulles. Session de préparation bornée à une heure,
liée au conseiller et à un identifiant de dépôt ; un onglet antérieur ne peut
réutiliser le rattachement d’un autre dépôt. UUID stable pour éviter les doublons
de soumission concurrente. CSRF et rôle contrôlés côté serveur.

Tests : `make test TESTS=tests.employers.test_adviser_deposit` ; couverture du dépôt
sans compte, partage, invitation ultérieure, révision, dates, rôles, CSRF et
révocation d’adhésion. Les services externes restent simulés dans les tests.

Validation locale du 20 novembre 2026 : suite de 821 tests réussie (8 ignorés),
19 tests spécifiques réussis dont calcul réel et migration aller-retour sur données
non vides ; 40 tests JavaScript et contrôles gettext/formatage/Django réussis.
Dépôt sans compte réalisé dans le navigateur, données fictives et Albert simulé.
Aucune publication, fusion ou mise en production.
