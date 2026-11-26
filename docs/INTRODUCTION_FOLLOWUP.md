# Suivi conseiller des mises en relation

La rubrique « Suivi des mises en relation » est commune à tous les conseillers
actifs. Elle couvre chaque revue par offre déjà engagée, avant et après ouverture
du fil à trois, y compris les dossiers devenus inéligibles : ils restent visibles
pour permettre un bilan et une clôture explicites.

## Parcours

- Lire l’étape calculée à partir des réponses, validations, accords et conversations.
- Enregistrer une prochaine action, la personne attendue et une date de suivi.
  Aucune échéance arbitraire n’est appliquée aux anciens dossiers.
- Ouvrir le suivi : les dossiers échus ou du jour sont présentés par défaut s’il
  y en a. Les filtres comptés distinguent aujourd’hui/retard, date à fixer, plus
  tard, tous les dossiers et les clôtures. Les échéances sont triées avant les
  dossiers sans date ; le retard et le temps restant sont exprimés en jours.
- Chaque fiche affiche qui doit agir, l’action proposée ou enregistrée, l’attente
  suivie et un bouton explicite vers l’examen, la date ou la relance. Le formulaire
  préremplit une action selon l’étape, sans attribuer de délai arbitraire.
- Relire et modifier le message de relance, choisir le destinataire et la langue
  de l’email, puis déclencher explicitement son envoi.
  La préparation de la date et la relance sont deux étapes numérotées ; clôture et
  historique sont repliables. Si l’email est indisponible, l’écran et le bouton
  annoncent explicitement un enregistrement sans envoi.
- Renseigner l’issue : en cours, embauché ou recrutement arrêté. Une clôture
  exige un motif, retire l’échéance et bloque les relances de ce suivi. Une
  réouverture se fait par une nouvelle sauvegarde explicite avec échéance.

L’issue est le bilan déclaré par le conseiller pour cette mise en relation, pas
une décision automatique ni une modification du profil, des accords ou du fil.
Le temps d’attente part de la définition de l’action et de la personne attendue ;
changer uniquement l’échéance ou envoyer une relance ne remet pas ce temps à zéro.

## Relances et confidentialité

Avant le fil commun, une relance candidat mène à sa revue privée. La relance
employeur exige une demande d’accord actuelle encore en attente, validée par le
conseiller responsable. Après ouverture, les deux destinataires sont possibles
si les accords et participants sont toujours actuels. Un refus, un retrait ou
une modification des conditions bloque la relance employeur périmée. Les refus
ne deviennent jamais automatiquement une absence de réponse.

Seul le texte relu et un lien personnel vers le dossier sont envoyés. Aucun
résumé privé Albert ni note de suivi n’est copié dans l’email ou le fil commun.
Les contrôles des pages de destination restent applicables. La langue choisie
concerne les libellés et le lien de l’email ; le texte modifié par le conseiller
est conservé tel quel, sans traduction automatique.

Le backend Django commun et `EMAIL_DELIVERY_ENABLED` s’appliquent. L’historique
distingue transport désactivé, tentative en cours, acceptation par le transport
et échec. Une acceptation ne prouve ni réception ni lecture. Pas de relance
automatique, de nouvelle tentative après échec ou de délai de réponse imposé.
Les doubles soumissions sont bloquées par une version sous verrou et un délai
de 60 secondes entre tentatives sur un dossier. Une réponse reçue pendant la
préparation invalide l’ancien formulaire de relance.

## Stockage et vérification

`IntroductionFollowup` conserve la prochaine action, l’attente, l’échéance,
l’issue, son motif, la version et le dernier conseiller intervenu.
`IntroductionFollowupEvent` conserve les sauvegardes et tentatives de relance,
avec auteur, date, destinataire, message et état d’envoi ; aucun lien de connexion
ni secret n’y est enregistré. Ces données sont réservées aux conseillers ;
l’administration permet seulement la consultation des identifiants.
Migrations additives `0026`/`0027`, sans reprise ni modification des anciens dossiers.

Vérifier avec `make test TESTS=tests.matching.test_introduction_followup` et
`make test TESTS=tests.matching.test_introduction_followup_migration`, puis les
contrôles communs `make check` et les cibles de formatage/gettext.
Pour une recette locale fictive : `make test-accounts-seed`, puis `make run PORT=9047`.
Le transport réel demeure à vérifier dans un environnement configuré autorisé.
