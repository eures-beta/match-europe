# Notifications Push des candidats

Le service est dans `eures_beta/candidates/push.py`, l'inscription HTTP protégée
dans `eures_beta/www/candidate/push.py` et le navigateur dans
`eures_beta/static/pwa/candidate-push.js`. Le profil adapté à l'application
installée utilise `candidates/pwa_profile.html`. Ces noms ne désignent pas une
recette : les comptes candidats autorisés suivent le même parcours partout.

## Clé d'envoi et renouvellement

Le contexte de dérivation est `b'match-europe-push-v1'`. Ce texte public n'est
pas un secret. Associé à la clé secrète Django par HMAC-SHA256, il permet de
dériver la clé privée P-256 VAPID qui authentifie les envois auprès des services
Push. À clé Django et contexte identiques, la clé d'envoi reste stable.

Ce changement de contexte effectue une rotation de la clé VAPID. Ne pas changer
la clé secrète Django pour cette opération : les sessions et liens de connexion
ne sont pas concernés. Aucun modèle ni schéma ne change ; aucun compte, profil,
offre ou abonnement en base n'est supprimé par un déploiement.

Un navigateur lié à l'ancienne clé ne peut pas recevoir les envois signés par la
nouvelle. À sa prochaine visite du profil dans l'application installée, si les
notifications sont déjà autorisées et que l'abonnement du navigateur correspond
à celui enregistré pour le candidat connecté, le JavaScript
compare les clés. Il réutilise l'abonnement actuel si elles correspondent ;
sinon il se désabonne de l'ancien et crée un nouvel abonnement avant de
l'enregistrer par POST avec CSRF. Le profil reste le propriétaire de
l'abonnement et la limite d'un appareil par candidat reste inchangée.

Un abonnement du navigateur appartenant à un autre compte ou appareil n'est pas
repris automatiquement : sur un navigateur partagé, l'autorisation du site ne
vaut pas inscription de tous les comptes qui s'y connectent.

Cette mise à jour ne demande aucune nouvelle permission et ne crée pas de premier
abonnement automatiquement. Sans abonnement ou sans autorisation préalable,
le candidat utilise le bouton « Activer les notifications ». Une erreur de
renouvellement ou d'enregistrement reste visible et permet un nouvel essai.

Les appareils qui ne reviennent pas sur le profil ne sont pas migrés à distance :
leurs notifications ne reprennent qu'après renouvellement. La rotation n'exige
aucune purge manuelle de la base. Les tests simulent tous les services Push et
ne prouvent pas la réception sur un téléphone réel.

En cas de retour à une version antérieure qui réutilise l'ancienne clé sans
gérer son renouvellement, les navigateurs déjà migrés doivent supprimer leur
abonnement dans les paramètres du site, puis réactiver les notifications. Ne pas
restaurer ou modifier la clé secrète Django pour contourner cette transition.

## Vérifications

- `make test TESTS=tests.candidates.test_push` : stabilité et rotation de la clé.
- `make test-js JS_TESTS=tests/candidates/push.test.cjs` : consentement, réutilisation,
  renouvellement, protection CSRF et échecs sans annonce de succès.
- `make test` et `make test-js` : interactions avec les parcours et droits existants.

Pour une vérification manuelle, autoriser les notifications sur une version
antérieure, puis ouvrir le profil sur la nouvelle version, sur la même origine
HTTPS. Vérifier le renouvellement, puis l'envoi depuis un conseiller autorisé.
Avec un nouveau navigateur, vérifier qu'aucune permission ni souscription n'est
demandée avant l'action sur le bouton. Tester également le refus des notifications.
