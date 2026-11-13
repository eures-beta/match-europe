# Import réservé aux comptes employeurs

L’accueil employeur et la confidentialité restent publics. Les pages d’import
FR/EN/DE, leurs variantes et les API de lecture/enregistrement exigent désormais
un compte actif de rôle employeur. Ni conseiller ni superadministrateur ne
contournent ce contrôle. La CSRF et les protections réseau des lecteurs restent
actives.

Sans ce rôle, une page explique comment contacter un conseiller pour obtenir
un compte et propose la connexion. Un compte connecté d’un autre rôle doit
explicitement se déconnecter pour utiliser un employeur. Aucune inscription
automatique ni création implicite de compte n’est introduite.

La reprise après lien magique (y compris dans un autre navigateur) accepte
uniquement six chemins d’import fixes dans `users/login_return.py`. Les URL
externes, les destinations arbitraires et l’administration sont refusées. Le
sélecteur de comptes fictifs reprend lui aussi l’import en recette. Hors de ce
contexte, les liens de connexion continuent d’ouvrir le tableau de bord.

## Enregistrement

La lecture initiale conserve la source dans la session, associée au compte, sans
créer d’offre. À l’enregistrement de l’étape contact, `EmployerImport.created_by`
et son adresse d’accès proviennent exclusivement du compte connecté, jamais des
champs soumis. Les coordonnées du contact métier peuvent être différentes.
L’offre reste privée au compte (`company=NULL`, pas d’adhésion créée implicitement),
apparaît immédiatement dans son tableau et persiste après déconnexion. Un import
ne peut pas réutiliser la source préparée par un autre compte. Si la session a
expiré, aucune offre anonyme n’est créée.

Ce nouvel enregistrement ne déclenche pas d’envoi externe ; les autres opérations
du parcours conservent leurs protections. Le plafond existant de 30 imports
s’applique maintenant au compte plutôt qu’au navigateur. Les anciens brouillons
anonymes ne sont plus accessibles via cette API ; aucune donnée ancienne n’est
supprimée ni attribuée par simple correspondance d’e-mail.

Aucun nouveau modèle ni migration. Les brouillons contiennent le texte de l’offre
et les coordonnées de contact : ce sont des données persistées, pas seulement
une simulation dans le navigateur. La session conserve temporairement la source
et l’intention de reprise ; les règles de session existantes restent applicables.

Tests : `make test` et `make test TEST_ARGS='-k employer -k occupation'`. Les tests d’anciennes pièces non
réclamées utilisent des fixtures explicites en base pour vérifier leur reprise,
sans rouvrir la création anonyme dans l’API.
