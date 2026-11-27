# Automatisation GitHub

`python-update.cjs` publie les deux verrous préparés par `make python-update`.
Le workflow hebdomadaire s'arrête si le catalogue officiel Clever est illisible ;
aucune version d'une branche absente ou en fin de vie n'est proposée.
Voir [la maintenance Python](../docs/PYTHON_RUNTIME.md).

[workflows/](workflows/) contient les contrôles de qualité et les signaux de recette.
La validation PostgreSQL complète garde tous ses contrôles et dispose de 30 minutes,
notamment pour les migrations aller-retour ; voir [les tests](../docs/TESTS.md).
Les contrôles qualité valident le push interne ou la PR d’un fork, sans annuler
une validation en cours à cause du second événement de la même PR.
`preview-request.yml` reçoit les événements de PR sans checkout ni secret.
`preview-relay.yml` s’exécute depuis main et transmet uniquement l’identifiant du
signal au contrôleur privé ; aucun code de la PR n’est exécuté avec ses secrets.

Le relais tente au maximum quatre transmissions : immédiatement, puis après
10, 30 et 60 secondes d’attente entre les essais. Chaque appel est limité à
15 secondes. Les erreurs réseau, délais dépassés, HTTP 429 et 5xx sont réessayés ;
les autres erreurs arrêtent immédiatement le relais. Retry-After peut augmenter
l’attente jusqu’à 60 secondes ; au-delà, le relais demande une relance ultérieure
plutôt que solliciter GitHub trop tôt. Le job reste borné à six minutes.

Toutes les tentatives conservent le même signal. Un POST peut avoir abouti malgré
une réponse perdue : le contrôleur privé sérialise ses exécutions et réconcilie
l’état actuel des PR, sans créer une génération à chaque appel. Les reprises ne
changent ni les labels ni le bail calculé depuis leur ajout.

Si toutes les tentatives échouent, relancer le job du relais depuis GitHub Actions,
sans retirer puis remettre le label recette : cette manipulation peut recréer une
base vide. La PR contenant ce changement doit être fusionnée pour activer les
reprises automatiques ; ses tests ne contactent aucun service réel.

Régression hors ligne : `make test-js JS_TESTS=tests/config/preview_relay.test.cjs`.
