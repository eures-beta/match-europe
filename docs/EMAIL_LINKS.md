# Liens cliquables et présentation des e-mails

## Présentation partagée

Les invitations employeur disposaient d'une carte claire de largeur limitée,
d'une police Arial, d'un bouton bleu et d'un pied de page avec les partenaires.
Les messages transactionnels avaient seulement des paragraphes HTML. Tous les
e-mails applicatifs utilisent désormais [le même gabarit](../eures_beta/templates/emails/) :
fond clair, carte de 640 px maximum et largeur fluide, titres, bouton lorsqu'une
action est fournie explicitement, mentions et logos existants. Les invitations
candidat et conseiller conservent leur contenu et leur politique de langue actuels.
La signature personnelle des invitations employeur reste celle du conseiller.

Les textes simples, destinataires, jetons, durées et règles d'envoi sont conservés.
Le HTML n'interprète jamais le texte utilisateur comme du balisage. Le pied de page
transactionnel n'utilise que l'origine configurée et validée ; les aperçus sans
transport configuré restent rendables. Les adresses longues se replient visuellement
sans caractère ajouté au lien. Les logos reprennent les fichiers existants et ne
sont pas indispensables pour comprendre le message ou ouvrir l'action.

Le CSS des e-mails est intégré dans les attributs, sans Bootstrap externe,
JavaScript, police distante ni pixel de suivi ajouté. Les tableaux de mise en page
ont `role="presentation"`. Ce gabarit centralise les valeurs existantes de l'e-mail
employeur plutôt que les dupliquer dans chaque parcours ; les pages web continuent
d'utiliser leurs tokens et feuilles CSS. Les rendus réels dans les logiciels de
messagerie restent à vérifier après livraison autorisée.

## Constat et inventaire

Audit du code le 23 novembre 2026. Un lien reconnu automatiquement dans Gmail
ne garantit pas sa reconnaissance dans un autre client. Les destinataires
concernés et leur configuration restent à identifier ; la cause de leurs
signalements n'est donc pas prouvée par cet audit statique.

| Famille envoyée | Format avant correction | Présentation retenue |
| --- | --- | --- |
| Connexion commune candidat/employeur/conseiller | Texte seul, URL personnelle complète | Texte + HTML avec lien explicite |
| Connexion employeur après dépôt conseiller | Même texte de connexion | Même rendu commun |
| Confirmation du profil candidat | Texte seul, URL signée | Texte + HTML avec lien explicite |
| Invitation employeur simple | Texte seul, URL signée | Texte + HTML avec lien explicite |
| Invitation/relance employeur, candidat ou conseiller depuis le panneau | Texte + HTML, bouton et confidentialité | Bouton conservé + adresse personnelle complète à copier |
| Proposition d'offre au candidat | Texte seul, lien personnel avec destination | Texte + HTML avec lien explicite |
| Notifications de réponses et de décision conseiller | Texte seul, lien vers le dossier privé | Texte + HTML avec lien explicite |

Les deux entrées de connexion partagent `users/login_email.txt`.
Les invitations enrichies ont cinq templates HTML : le rappel employeur réutilise
l'invitation ; le rappel conseiller utilise la même structure que l'invitation.
Les liens de confidentialité déjà présents restent des ancres HTML.
L'inventaire couvre les appels applicatifs `send_mail` et `EmailMultiAlternatives`,
pas les notifications émises par les prestataires d'hébergement ou de messagerie.

## Contrat de rendu

- Envoyer `multipart/alternative` : texte lisible d'abord, HTML ensuite, selon
  [MIME RFC 2046, §5.1.4](https://www.rfc-editor.org/rfc/rfc2046.html#section-5.1.4).
  Django le produit avec le paramètre `html_message` de
  [`send_mail`](https://docs.djangoproject.com/en/6.1/topics/email/).
- Le texte existant reste la source du contenu transactionnel et de ses
  traductions. `emails.rendering.html_email` ajoute une présentation HTML commune,
  échappe les contenus et transforme les URL en véritables `<a href="…">`.
  Les liens restent compréhensibles même sans images, scripts ou styles chargés.
- Afficher l'adresse complète, sans raccourcisseur ni nouvelle redirection de
  suivi, et une consigne de copie en FR/EN/DE. Les invitations riches gardent leur
  libellé d'action et ajoutent aussi l'adresse visible.
- Garder les origines de confiance, paramètres, jetons et destinations. Django
  peut percent-encoder un caractère réservé dans un `href` : le jeton décodé et
  la destination doivent rester identiques. Aucun retour à la ligne ou caractère
  invisible n'est inséré dans une URL. L'encodage MIME est confié à Django.
- Ne pas rendre un lien cliquable en tant qu'image, dépendant de JavaScript ou
  d'un formulaire. Le HTML simple reste utilisable sans CSS.
- La présentation ne modifie pas l'expiration ni les droits. Un GET de scanner
  de sécurité ne doit pas consommer le lien : la confirmation POST/CSRF reste.

## Limites et validation chez les destinataires

Un véritable lien HTML peut encore être désactivé par le client ou une passerelle
anti-hameçonnage. Microsoft documente ces restrictions dans
[Outlook pour Windows](https://support.microsoft.com/en-us/outlook/links-are-disabled-in-outlook-for-windows-email-messages).
Ne pas recommander de désactiver globalement la protection pour résoudre le cas.

Pour un signalement, relever le client/version, mobile ou ordinateur, dossier
normal ou indésirable, aspect du lien et éventuel avertissement. Distinguer lien
impossible à cliquer, ouverture bloquée et page ouverte avec lien expiré.
Ne pas publier un lien magique, son jeton ou le message original privé dans une PR.

Les tests reconstruisent le MIME et vérifient texte/HTML, paramètres signés longs,
retours encodés, échappement HTML, FR/EN/DE, secours des cinq templates riches et
les parcours réels en boîte mémoire : connexion, dépôt conseiller, inscription,
invitation, proposition d'offre et notifications. Aucun e-mail réel n'est envoyé.

Commande : `make test TESTS='tests.emails tests.users.test_magic_login tests.candidates.test_registration tests.invitations tests.employers.test_adviser_deposit tests.introductions.test_review_email tests.introductions.test_review_workflow'`.
Compléter par les contrôles habituels et une réception manuelle dans les clients
concernés après livraison autorisée. Les tests MIME ne valent pas une validation
visuelle sur Gmail, Outlook, Thunderbird ou Apple Mail.
