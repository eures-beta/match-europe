# Proposition d’offre par email

Après validation du matching par un conseiller, la transaction crée ou retrouve
la revue de l’offre. Après commit seulement, `matching/review_email.py` tente
l’email dans la langue FR/EN/DE du candidat. Ce déclenchement n’envoie plus de Push.
Un refus de matching n’envoie rien. Aucun profil n’est transmis par l’email.

Le message présente le poste et le lieu, Albert, les réserves possibles et le
consentement distinct. Le lien personnel utilise django-sesame et l’origine
HTTPS de confiance `LOGIN_EMAIL_ORIGIN`, jamais l’en-tête Host. Il expire après
une heure et une connexion l’invalide. Un GET ne connecte personne : une
confirmation POST protégée par CSRF précède le dialogue de l’offre concernée.
La demande d’un nouveau lien garde cette destination. Un autre rôle ou candidat
n’accède pas à cette revue, même avec une destination modifiée.

## Suivi et relance

Dans l’espace candidat, une proposition validée apparaît même si l’email échoue.
Le profil signale les nouvelles offres ; la liste donne accès au dialogue ou à
la relecture. Le badge « Nouvelle offre » signifie qu’aucune réponse n’a encore
été enregistrée, pas que l’email ou la page n’a pas été lu.

États calculés, sans migration : « À commencer », « En cours », « Terminé » après
un choix de transmission enregistré (y compris un refus), et « Offre refusée »
si le poste ou l’employeur est refusé. Toutes les réponses ne suffisent pas à
terminer : la relecture et le choix de partage restent distincts. Un contexte
modifié qui invalide l’accord rouvre le parcours sans le présenter comme nouveau.

`CandidateOfferReview.email_status`, `email_attempted_at` et `email_sent_at`
conservent le statut du transport, la dernière tentative et le dernier succès.
Ils ne conservent ni lien personnel, ni corps d’email, ni erreur du fournisseur.
La migration additive `0017_offer_review_email` laisse les revues existantes
en attente : aucun rattrapage automatique des anciennes propositions.

Le conseiller voit si le transport est absent/désactivé, en cours, en échec ou
accepté par le service de messagerie. Ce dernier statut ne prouve ni réception
ni lecture. Une validation répétée ne renvoie pas d’email. Le bouton de relance
est un POST réservé aux conseillers actifs, limité par revue en base : une minute
entre tentatives, cinq minutes si un envoi est encore marqué en cours.

Le transport Django commun exige `EMAIL_DELIVERY_ENABLED=1` et sa configuration
SMTP. En local fictif, il reste désactivé ; les tests utilisent la boîte mémoire.
L’absence de transport et un échec SMTP ne défont pas la décision du conseiller.

## Limites et vérifications

Envoi synchrone après commit, délai SMTP commun de dix secondes, sans file
durable ni relance automatique. Une interruption après commit mais avant l’envoi
peut laisser une revue en attente ; la relance manuelle la reprend. Un arrêt
après acceptation SMTP et avant enregistrement du résultat laisse un état
incertain ; une relance peut produire un doublon. La livraison exactement une
fois n’est pas garantie par SMTP.

`make test TESTS=tests.introductions.test_review_email` couvre déclenchement, absence
de Push, erreurs, relance, langues, authentification et retour sur la bonne offre.
Les tests simulent les services externes : ils ne prouvent pas la délivrabilité
du fournisseur ni le ton réel d’Albert. Aucune configuration distante n’est
modifiée par ce lot.
