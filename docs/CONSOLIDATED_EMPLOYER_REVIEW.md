# Recette consolidée du parcours employeur

Préparation du 23 octobre 2026, autorisée par Eric. Branche dédiée
`codex/consolidated-employer-review`, sans fusion ni modification des PR sources.
Cette branche sert à tester ensemble les évolutions ; elle ne vaut pas une
proposition de fusion de tous les lots dans leur état actuel.

## Sources intégrées

- PR #2, tête `57670e2` : prototype, point d’entrée employeur, HTTPS, sessions,
  protections CSRF, sonde et initialisation fictive non destructive.
- PR #14 (`7129ec6`) et #15 (`c07b25b`) : lecteur PDF/images/OCR et logo fourni.
- PR #16 (`6f098a1`), #18 (`4c8bcc6`), #19 (`c56d5d0`), #20 (`ded96d9`),
  #21 (`8ca94ce`), #22 (`ca741c4`) : chaîne employeur complète publiée.
- PR #23–#24 : commandes Make utiles et contrôle Black 26.10.1 repris et
  adaptés au prototype ; formatage appliqué au code consolidé.
- Recette locale intégrée : messages OCR et avertissements repris dans les
  sources JSON et les écrans FR/EN/DE. Les champs d’identification officielle
  abandonnés ne sont pas ajoutés à la nouvelle base. Le rattachement simplifié
  publié dans #19 est conservé ; aucune donnée locale existante n’est supprimée.

La PR #6 conserve un autre découpage historique du prototype, sans évolution
fonctionnelle à ajouter ici. Les correctifs de rattachement locaux abandonnés
ne sont pas réintroduits.

## Adaptations à la démonstration HTTPS

Le mode `SHARED_DEMO` autorise la connexion email simulée en HTTPS et conserve
les contrôles de session et d’appartenance. Les écrans de test ne sont pas une
authentification de production : utiliser exclusivement des identités fictives.
La boîte simulée reste propre à la session qui a demandé le lien ; les identités
et établissements persistants de la démonstration ne doivent contenir aucune
coordonnée réelle. Aucun email n’est envoyé.

Le mode partagé active la simulation de recherche et bloque préparation externe
et géocodage. Les liens publics d’offres peuvent être lus à la demande de
l’utilisateur, avec les validations réseau existantes. Le diagnostic Push reste
refusé. Les imports restent distincts du modèle de matching `Offer`.

Migrations additives `0005` à `0008` : liens de connexion fictifs, identités et
établissements, duplication et opérations/événements de recherche simulée.
Elles sont appliquées à une base dédiée ; aucune base de recette existante n’est
réutilisée pour cette consolidation.

## Vérifications locales effectuées

- 144 tests PostgreSQL passent, dont trois tests d’intégration HTTPS : import,
  connexion, rattachement, recherche simulée, verrouillage, duplication,
  isolation entre testeurs et CSRF.
- Migrations sur base vide, contrôle Django, absence de migration manquante,
  collecte de 135 ressources statiques et contrôle Black réussis.
- Syntaxe des JS/CJS et lecture des JSON vérifiées ; catalogues FR/DE compilés.
- Lecture réelle d’un PDF fictif et OCR réel de son image : intitulé, lieu et
  avertissement de contradiction 40 h / 20 h retrouvés.
- Navigateur local : accueil, connexion simulée et tableau employeur vérifiés.

Le premier essai distant a confirmé l’accueil FR/EN/DE et la lecture PDF
textuelle, mais a échoué pour une image. Un secours OCR portable a donc été
ajouté : même moteur Tesseract via Tesserocr, rendu PDFium, images Pillow et
modèles officiels FR/EN/DE livrés dans le dépôt (environ 6,8 Mo, licence Apache
2.0). Le moteur épinglé et ses modèles sont prioritaires ; les outils système restent un secours. Aucun service OCR distant
ni téléchargement au traitement d’un document. Cette adaptation reste à
revérifier après redéploiement.
Aucune certification de conformité ou d’accessibilité complète n’est revendiquée.

## Parcours à essayer

1. Ouvrir `/` : accueil employeur français ; vérifier EN/DE.
2. Ajouter un PDF fictif, une image ou du texte ; relire les champs et avertissements.
3. Corriger avant le contact, puis enregistrer avec un email fictif.
4. Ouvrir l’email simulé, confirmer et rattacher explicitement l’offre à un établissement.
5. Retrouver l’offre dans le tableau, la consulter et la modifier.
6. Lancer une recherche simulée, essayer succès/échec/incertitude et vérifier le verrouillage.
7. Dupliquer l’offre et vérifier que la copie reste modifiable.
8. Avec une autre identité fictive dans un autre navigateur, vérifier l’absence d’accès à cet établissement.

La disponibilité distante et le commit déployé sont à consigner après publication.


Le traitement OCR portable borne le côté le plus long à 1 200 pixels (900 pixels de largeur pour les images) afin de réduire la mémoire. Une image fictive réduite à 1 200
pixels a réussi sur la recette alors que l’original provoquait une erreur de
passerelle ; cette observation motive la borne. Les petits caractères et les
scans dégradés restent à contrôler humainement ; aucune précision universelle
n’est promise.
