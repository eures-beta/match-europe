# Dialogue privé candidat avec Albert

## Parcours et consignes

Après une demande du conseiller, le candidat examine une offre dans son espace
privé. Le serveur choisit les étapes ; Albert accompagne les réponses libres.

1. Intérêt pour le poste en premier. Expliquer le rapprochement avec au plus deux
   compétences communes explicitement déclarées et reconnues par le calcul.
   Aucun rapprochement de libellés ni métier ne permet d'inventer une compétence.
   Sans compétence commune établie, poser simplement la question d'intérêt.
2. Conditions déterminantes de cette offre : horaires, disponibilité, mobilité,
   contrat, salaire, autorisations, compétences et langues. Les déclarations du
   profil restent un point de départ, pas une confirmation pour cette offre.
3. Intérêt pour l'employeur en dernier : « C’est {employeur} qui recrute.
   Tu te verrais travailler chez eux ? ». Le connaître ne signifie pas accepter
   d'y travailler. Ne pas demander de justification obligatoire pour un refus.
4. Relecture du résumé et des réserves, puis permission de transmission distincte
   dans le formulaire existant. Aucun envoi automatique ni accord employeur déduit.

Le prompt `matching/dialogue_albert.py` demande des phrases courtes, naturelles,
une seule question utile à la fois et des relances liées aux mots du candidat.
Pas de flatterie, de pression, de répétition mécanique ou de réponse inventée.
Une hésitation n'est pas un oui ; une réserve reste une réserve. Une information
absente de l'offre est à préciser par le conseiller, jamais à inventer.

Un refus du poste ou de l'employeur arrête la proposition, sans modification du
profil ni effacement de la décision conseiller. Le candidat peut corriger sa réponse.
Une demande de précision sur le poste ou l'employeur reste à confirmer. L'employeur
non identifié empêche une autorisation de transmission ; une réserve employeur
explicite peut rester dans le résumé soumis à la décision humaine.

## Garanties de l'application

Propriété, rôle candidat actif et profil vérifié, CSRF, quotas, signatures et
empreintes du contexte sont vérifiés côté serveur. Les réponses et consentements
restent liés à l'offre et deviennent périmés si le contexte pertinent change.
Les anciens consentements ne dispensent pas de répondre à la nouvelle question
employeur. Les réponses utilisent
`CandidateOfferReviewAnswer`, la permission `CandidateProfileSharing`.
Le suivi durable est décrit dans [le contrat de clôture](REVIEW_HANDOFF.md).

Albert ne choisit pas la prochaine étape et ne dispose d'aucun outil d'écriture,
de score, d'envoi ou de transmission. Une réponse libre est une proposition à
relire et confirmer. Les modifications générales autorisées passent par le
brouillon de profil puis par ses formulaires et sa validation explicite.
Le poste et l'employeur ne peuvent pas produire de modification générale.
Les champs proposés exigent une preuve exacte dans les paroles du candidat ;
cette preuve ne remplace pas la relecture sémantique humaine.

## Données et transport

Client commun `integrations.albert`, JSON borné, sans outils ni streaming.
Le contexte contient la langue, la question, les conditions correspondantes,
les déclarations utiles et les échanges de cette condition ; pas le profil entier
ni les coordonnées candidat. Les compétences communes sont des références
traçables ; la question affichée contient leurs libellés traduits.
Pour la question employeur, son nom enregistré est nécessaire au dialogue.

Historique signé de quinze minutes, au plus six messages historiques et 2000
caractères de paroles candidat ; six tentatives réseau par quinze minutes.
Délai de 25 secondes, réponse limitée à 20 ko et 1800 tokens ; pas de relance
automatique. Une réponse hors schéma ou indisponible renvoie vers le formulaire
guidé sans écriture. Les messages sont échappés, HTML et liens modèle refusés.

Même parcours en local, recette et production avec le service configuré.
`ALBERT_SIMULATED=1` choisit explicitement le simulateur et interdit l'appel réel ;
sinon une clé privée est requise. Les tests automatisés simulent le transport.
Les textes libres peuvent contenir des données sensibles ; conservation, purge
et cadre de traitement doivent être évalués pour l'usage réel.

## Vérifications

- `make test TESTS=tests.matching` : parcours complets, refus, réserves, consentement,
  contexte modifié, droits, CSRF et transport simulé en FR/EN/DE.
- `make check`, `make format-check`, `make format-html-check`,
  `make translations-check translations-compile` : contrôles communs.
- `make run PORT=9045` : essai local avec la configuration du worktree.
- `make dialogue-live-evaluate` : évaluation réelle explicitement choisie, six
  échanges fictifs au plus, sans base. Consomme le quota du service.

Les tests simulés ne prouvent ni le ton du modèle réel, ni sa disponibilité,
ni l'absence d'hallucination. Un essai métier réel et une vérification sur téléphone
restent distincts de la validation automatisée.
