# Confirmation et enregistrement candidat — premier lot P1

## Périmètre et activation

Lot empilé sur #131. À la demande d'Eric, les quatre étapes du questionnaire
peuvent préparer un compte et une fiche après confirmation d'e-mail, puis
permettre au candidat de consulter et modifier ses propres réponses.

Ce premier lot est **un essai local/recette avec données fictives**. Le réglage
`CANDIDATE_REGISTRATION_ENABLED=0` est désactivé par défaut. L'activation exige
`DJANGO_ENVIRONMENT=local` ou `preview` et les emails réels désactivés, en plus
des protections d'accès de démonstration. Un démarrage en production avec ce
réglage activé est refusé. Les nouvelles routes répondent 404 hors essai.
Les adresses doivent se terminer par `.invalid` ; aucun transport e-mail n'est
appelé. L'autorisation de ce lot ne vaut pas ouverture aux données réelles.

## Parcours

1. Questionnaire anonyme en quatre étapes, ESCO/ROME toujours indépendants.
2. Dernière étape : nom d'affichage, email fictif obligatoire, relecture et lien
   vers la notice. La case constate une lecture, pas une nouvelle base juridique.
3. Revalidation serveur de toutes les étapes ; seuls les champs du profil sont
   conservés dans une demande temporaire. Aucun compte n'existe à ce stade.
   Le brouillon de session est retiré après la demande.
4. L'opérateur simule l'email en privé. Le lien signé contient un identifiant et
   un nonce, jamais les réponses ou l'adresse email. GET mémorise le lien dans
   la session et redirige vers une URL propre ; il ne crée rien.
5. Confirmation POST avec CSRF : verrou PostgreSQL, compte candidat et fiche
   créés atomiquement, demande supprimée, session connectée et renouvelée.
   Un lien consommé, falsifié ou expiré ne crée ni compte ni profil.
6. `/candidate/profile/` est réservé au candidat propriétaire. Modification par
   un POST protégé, puis questionnaire prérempli et nouvelle validation complète.
   L'email du compte est affiché désactivé et n'est pas modifié par ce parcours.

Un compte existant (y compris inactif, conseiller ou employeur) n'est ni converti
ni remplacé. Un candidat existant utilise la connexion habituelle pour retrouver
son profil. Un compte candidat actif sans fiche peut recevoir sa première fiche
après la même vérification email, sans créer de second compte. Une demande non
confirmée existante n'est pas remplacée par un autre
visiteur. La page de résultat reste neutre et n'affiche ni adresse ni jeton.
Les limites PostgreSQL communes par adresse et IP s'appliquent aux soumissions.

## Données et conservation

- `candidates.CandidateRegistration` : UUID, nonce, email normalisé, langue,
  réponses validées, création et échéance. Migration additive `0002`.
- Délai d'essai retenu : **une heure**, contrôlé à la fois par signature et date
  stockée. Ce délai ne concerne pas les invitations employeurs ni les profils.
- Après confirmation, les réponses temporaires disparaissent de la demande.
  Les demandes expirées sont effacées lors d'une nouvelle demande ou par la
  commande de nettoyage. Pas de tâche planifiée installée : l'échéance d'accès
  ne garantit donc pas la purge physique exactement à la minute prévue.
- `CandidateProfile` reçoit par `0003` une date de vérification email, la date
  de lecture déclarée et la version de la notice. Les profils antérieurs gardent
  des valeurs vides : aucune vérification ou lecture rétroactive n'est inventée.
- L'administration de la demande est en lecture seule, limitée aux UUID/dates ;
  ni email, réponse ou nonce ne sont exposés dans ses listes ou détails.
- La migration inverse de `0002` supprime la table des demandes et son contenu ;
  celle de `0003` retire les métadonnées de vérification/notice. Le profil et les
  comptes préexistants sont conservés. Aucun retour arrière réel automatique.

Les 12 mois après dernier contact utile restent la règle de référence pour le
profil confirmé, issue de Flask et de la notice commune. Ce lot n'implémente pas
sa purge automatique et ne prétend pas que `updated_at` est un dernier contact
utile. Avant ouverture réelle : définir ce jalon, implémenter la suppression et
les sauvegardes, compléter les mentions juridiques, planifier et superviser les
nettoyages, puis raccorder un transport de production protégé dans un autre lot.

## Essayer et vérifier

- `make install-test` et `make install-quality` pour ce worktree ; `.env` et
  PostgreSQL dédiés, puis `make migrate`.
- `make candidate-registration-run` ouvre l'essai sur le port 9035 :
  `/candidate/prepare/?lang=fr` (EN/DE disponibles).
- À la fin du questionnaire, `make candidate-email EMAIL=personne@example.invalid
  ORIGIN=http://127.0.0.1:9035` imprime un email simulé privé. La commande ne
  transmet rien. Ne pas publier sa sortie : le lien autorise une connexion.
- `make candidate-registration-cleanup` compte sans effacer ;
  `make candidate-registration-cleanup CLEANUP_ARGS=--apply` efface uniquement
  les demandes fictives expirées, jamais les profils ou comptes.
- `make candidate-registration-test` : création atomique, POST/CSRF, expiration,
  rejeu, conflit de compte et de demande, droits, édition, traduction, nettoyage,
  simulation email et confirmation concurrente PostgreSQL.
- `make candidate-test`, `make test`, `make check`, `make users-upgrade-test`,
  `make format-check`, `make format-html-check`, `make translations-check`.

Aucun e-mail réel, appel de matching, partage conseiller/employeur ou fusion
n'est déclenché. Les fusions restent à dejafait.
