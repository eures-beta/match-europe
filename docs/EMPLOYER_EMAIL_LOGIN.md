# Connexion employeur : recette email locale

## Périmètre de cette PR

Première fonctionnalité isolée, basée sur la PR nº 16 : saisir une adresse
fictive, afficher « Consultez votre email », consulter le contenu du message
simulé, vérifier l’adresse et ouvrir une session employeur minimale au design
V2. FR/EN/DE. Aucun service externe, aucune modification des logos ou du lecteur
PDF. Les routes d’import et leurs scripts ne sont pas modifiés : cette PR ne
redirige pas encore le dépôt d’offre vers la connexion.

Activer explicitement `ME_EMPLOYER_EMAIL_LOCAL=1` dans un serveur lié à
`127.0.0.1`. Les vues exigent aussi le mode démonstration et une adresse cliente
loopback. Entrée : `/employer/access/`. Mode désactivé : routes introuvables.
La feuille de style utilise la route locale déjà existante de prévisualisation,
qui nécessite `ME_EMPLOYER_LOCAL_API=1`.

## Sécurité et simulation

Migration additive `0005_employer_email_link` : email, empreinte SHA-256 du
jeton aléatoire, expiration (15 minutes), consommation. Le jeton brut n’est
conservé que dans la session serveur pour livrer le message de recette ; il
n’est pas stocké dans la table des liens. La consommation est atomique sous
verrou PostgreSQL. GET ne consomme rien ; validation et déconnexion exigent
POST et CSRF. Rotation de clé de session à la connexion, session d’une heure.
Les journaux existants masquent les chemins contenant les jetons.

Les messages de recette sont visibles uniquement dans le navigateur demandeur.
Un lien copié reste utilisable sur un autre navigateur : son détenteur peut
s’authentifier une seule fois. Les demandes sont limitées à une par minute par
session et cinq par adresse sur quinze minutes ; les nouveaux liens invalident
les précédents. Ce contrôle local n’est pas une protection anti-abus de production.

L’email simulé utilise un formulaire POST pour arriver directement dans l’espace
sans écran intermédiaire. Un vrai email ne peut pas utiliser ce formulaire :
le transport Brevo et le parcours réel anti-scanner restent à concevoir et tester.
Aucune adresse d’expéditeur institutionnelle n’est inventée.

## Limites et lots suivants

La session contient un email vérifié localement, pas encore un compte utilisateur
durable. Aucun droit sur les entreprises, candidats ou offres n’est accordé.
La page d’accueil est minimale, sans compteurs fictifs ni tableau de bord.

Lots séparés : identité durable et rattachement explicite du brouillon ; liste
« Mes offres » et reprise ; ouverture/fermeture/archivage. Le rattachement doit
conserver l’accès lors de la rotation de session et ne jamais rechercher tous
les imports par simple correspondance d’email. Aucun envoi AGLAE ne doit être
provoqué par la connexion.

Recette : utiliser une adresse `.invalid`, ouvrir le message simulé puis
« Vérifier mon adresse email ». Vérifier le refus d’un lien réutilisé/expiré,
la déconnexion, la reconnexion et les trois langues. Les tests utilisent une
base PostgreSQL jetable et n’envoient aucun email.
