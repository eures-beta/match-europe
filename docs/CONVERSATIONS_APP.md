# Application conversations

`eures_beta/conversations/` porte les modèles Conversation/Message, le formulaire,
les vues, les permissions d’accès et les routes de discussion. Le rapprochement
candidat–offre reste dans `journeys`, qui ouvre une conversation après les accords.
Les URL et leurs noms restent inchangés. Le template est `conversations/detail.html`.

Les migrations déplacent la propriété des modèles dans l’état Django sans créer,
supprimer ou copier les tables existantes. `journeys_conversation` et
`journeys_message` conservent leurs noms, leurs identifiants et leurs données.
Les types de contenus sont réétiquetés en conservant leurs identifiants : les
permissions déjà attribuées restent liées. Leur nom applicatif devient néanmoins
`conversations.view_conversation`, etc. ; adapter tout consommateur externe qui
emploierait encore les noms `journeys.*` de ces deux modèles.

`make test` inclut un test PostgreSQL de migration aller-retour avec un message
existant et une permission attribuée. L’accès reste limité aux trois participants
vérifiés ; le rôle administrateur ne donne aucun accès général aux conversations.
