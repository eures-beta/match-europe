# Lecteur local des documents employeur

Travail local du 20 octobre 2026, sur une branche dédiée. Aucun commit, push ou déploiement autorisé avant la recette d’Eric.

## Fonctionnement

- Un PDF (30 pages maximum) ou jusqu’à huit images PNG/JPEG de la même offre, sélectionnées dans l’ordre de lecture. Taille totale maximale : 10 Mo.
- Extraction du texte PDF dans un processus séparé. Pour une page scannée ou une image, reconnaissance locale avec Tesseract. Aucun document n’est envoyé à un service d’OCR externe.
- Nettoyage des en-têtes d’impression et arrêt aux sections de candidature et d’offres similaires reconnues.
- Extraction prudente des champs : intitulé, entreprise, lieu, contrat, horaires, rémunération explicite, expérience, français avec niveau explicite, permis et qualification.
- Répartition des phrases sources entre missions/conditions et compétences/expérience, à partir des rubriques et d’indices FR/EN/DE. Les lignes coupées sont réunies ; tâches et exigences sont présentées en listes. Les nuances obligatoires/souhaitées restent dans les formulations d’origine. Les sections d’entreprise, candidature et entretien reconnues sont exclues de ces champs. Ce tri reste fondé sur des règles : phrases mêlant plusieurs sujets et rubriques inconnues peuvent nécessiter une correction humaine. Les anciens brouillons ne sont pas retraités automatiquement.
- Les contradictions reconnues sont affichées dans la préparation et la revue. Les horaires contradictoires restent vides. L’employeur vérifie les champs avant validation.
- Les images sont traitées dans l’ordre de sélection et les lignes strictement identiques sont dédupliquées. Les recouvrements partiels ne sont pas fusionnés sémantiquement.

## Dépendances OCR

Tesseract (`tesseract`) et Poppler (`pdftoppm` pour les PDF scannés) doivent être accessibles dans le PATH du serveur. Les modèles français, anglais et allemand sont recommandés ; le lecteur utilise les modèles disponibles parmi `fra`, `eng`, `deu`. Une installation dépourvue d’OCR peut toujours lire les PDF textuels ; un document nécessitant l’OCR échoue explicitement.

macOS : `brew install tesseract tesseract-lang poppler`. Linux : paquets Tesseract, modèles FR/EN/DE et Poppler du système. Ces dépendances locales ne constituent pas une préparation ni une autorisation de déploiement FT.

## Limites

Ce lecteur emploie des règles explicites, sans modèle génératif. Il ne garantit pas tous les formats. Une liste de niveaux d’expérience n’est pas convertie en ancienneté minimale. « Embauche directe » ne devient pas automatiquement CDI. La langue du texte n’est pas une exigence linguistique. Une adresse d’employeur n’est pas automatiquement le lieu de travail.

## Recette sans services externes

Lancer le prototype avec `ME_EMPLOYER_LOCAL_API=1 ME_LOCAL_REVIEW_ONLY=1 .venv/bin/python run_local.py` depuis `match_europe/`. Le second indicateur permet la lecture, la revue et l’enregistrement local des brouillons ; il bloque les appels AGLAE et le géocodage. La validation externe reste indisponible pendant cette recette. Les URL publiques demeurent une méthode d’import distincte qui lit le site demandé.

Attention : le parcours préexistant sans cet indicateur envoie une offre inactive à AGLAE sandbox dès la préparation lorsque les champs principaux sont renseignés. Un essai navigateur du 20 octobre a suivi ce parcours avant l’activation de l’isolement ; les essais suivants sont isolés.

Les sections de site inconnues, tableaux complexes, documents avec une mauvaise couche OCR et caractères mal reconnus restent à contrôler. La limite de texte est de 16 000 caractères. Les documents sources fournis pour la recette restent hors Git ; les tests versionnés utilisent des exemples fictifs.

Le parcours d’import reste distinct du modèle de matching `Offer`. Aucune migration de base, modification des permissions ou activation d’une intégration externe n’est incluse.
