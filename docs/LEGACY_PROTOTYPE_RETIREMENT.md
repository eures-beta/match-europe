# Retrait des quatre parcours historiques

L’ancien écran `/access/`, ses connexions fictives et sans mot de passe,
tableau de bord, dépôt de profil, offres de démonstration, préqualification,
conversations et notifications ne sont plus exposés. Leurs vues, formulaires,
templates et services spécifiques sont supprimés, ainsi que `seed_demo` et
l’initialisation automatique WSGI.

L’accueil `/`, `/candidate/`, les pages employeur et imports, les pages
statistiques/projet/journal, les trois langues, l’administration Django et les
sondes restent en place. `/employer/access/` appartient au parcours employeur
actuel : ce n’est pas l’ancien `/access/` et ses restrictions sont conservées.
Le diagnostic Push local reste distinct des anciennes notifications métier.

## Données et déploiement

La migration `accounts.0002` retire les quatre utilisateurs réservés
`adviser@example.invalid`, `employer@example.invalid`,
`candidate@example.invalid`, `admin@example.invalid`, et les objets de leur
scénario fictif. Elle refuse de supprimer une identité réservée qui aurait un
mot de passe utilisable ou des privilèges staff/superuser. Elle s’arrête aussi
si le conseiller fictif est lié à une offre d’un autre compte.

Les imports employeur actuels sont conservés ; une attribution à un conseiller
retiré est simplement remise à vide. Les autres utilisateurs ne sont pas
supprimés. Les sessions employeur ne sont pas purgées.

Les migrations et modèles de stockage historiques restent disponibles pour la
compatibilité des bases et leurs tests de migration ; aucun ancien parcours
HTTP ne les rend accessible. Leur suppression physique globale demanderait un
inventaire distinct des éventuelles données non fictives, qui ne sont pas
supprimées par cette PR.

La suppression des données fictives n’est pas annulable par un retour de code :
la migration inverse ne recrée pas les comptes. Une restauration nécessite une
sauvegarde. La PR n’exécute aucune migration sur un environnement distant.

## Stockage du parcours employeur conservé

La lecture URL/PDF/texte renvoie un résultat au navigateur et le place dans
`request.session['pending_offer_source']`. Avec le moteur de session Django
par défaut, cette session est elle-même enregistrée dans PostgreSQL ; elle
contient les champs extraits, pas le PDF source. Aucun `EmployerImport` n’est
encore créé à cette étape.

L’enregistrement du brouillon crée un `EmployerImport` : le JSON `data` contient
les champs extraits/corrigés, notamment la description ; contact, source et dates
sont enregistrés séparément. Pour une URL ou un PDF, la source temporaire est
alors retirée de la session. L’extraction seule et le dépôt final ne sont donc
pas la même étape. Le PDF original n’est pas conservé par cet import.

## Vérifications

`make test` couvre la disparition des routes même avec une ancienne session,
les pages conservées en FR/EN/DE, les imports et accès employeur, et le nettoyage
ciblé/idempotent des données. Les tests de migration historiques restent actifs.
