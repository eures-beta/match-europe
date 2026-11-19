# Catalogue commun des métiers et compétences

Catalogue partagé candidat et employeur. Périmètre : parcours candidat avec métier, parcours employeur, propositions Albert et présentation du matching. Le parcours candidat ouvert sans métier et ses secteurs éditoriaux ne sont pas élargis par ce lot.

## Une fiche métier, des références conservées

La recherche partagée utilise les 3 039 métiers ESCO 1.2.1 et 1 923 fiches ROME 26M10. Aucun nom de référentiel ni détail Sources n’est demandé à l’utilisateur. Les descriptions existantes sont conservées, sans inventer de métier ni de compétence. Les traductions manquantes ROME restent dans leur langue source française, correctement indiquée au navigateur ; la traduction intégrale n’est pas réalisée ici.

Le module `occupations/unified.py` n’autorise un regroupement que si la table officielle contient un `exactMatch`, que son appellation correspond à l’intitulé principal actuel de la fiche ROME et qu’une seule cible ESCO actuelle subsiste. Les correspondances larges, proches, ambiguës ou visant seulement une spécialité restent distinctes. Résultat du catalogue actuel : 398 fiches ROME regroupables ; les autres restent indépendantes. Le boulanger conserve sa description commune relue dans l’essai précédent.

La table officielle importée est France V1.1 (19 novembre 2025), ESCO 1.0.9 / ROME 25M06, jointe aux fiches 26M10 par OGR. Elle n’est pas présentée comme une table native des nouvelles éditions. Les versions et empreintes sont conservées dans les manifestes communs.

## Compétences officielles portables

`skills/data/common_skill_source.zip` et son manifeste contiennent 4 962 tranches indépendantes : une par métier ESCO et une par fiche ROME, ainsi qu’un index de libellés. Une tranche est lue sur demande ; le serveur ne charge pas toutes les relations en mémoire. L’archive et chaque tranche ont leur empreinte vérifiée. Cache mémoire borné à 64 tranches.

Le contrôle hors ligne compte 192 911 relations et 32 029 identifiants distincts, sans prétendre que des identifiants ESCO et ROME représentent des compétences équivalentes. Les savoir-faire et savoir-être ROME sont importés ; les diplômes et habilitations figurant dans les savoirs ne sont pas transformés en compétences. Les connaissances ESCO restent sourcées pour préserver les déclarations anciennes, mais ne sont pas proposées comme nouveaux savoir-faire par le repli ou la présélection dynamique.

Les listes d’un métier regroupé réunissent les relations officielles des deux sources. Les identifiants distincts restent distincts. Un libellé identique peut être écarté de la liste courte pour éviter de répéter la même proposition, sans créer une équivalence dans le matching. Les associations éditoriales de savoir-être des fiches préparées restent identifiées comme telles. Sans savoir-être ROME associé, les suggestions transversales existantes peuvent servir d’aide de lecture, sans prétendre à une relation officielle métier–savoir-être.

## Propositions et cache Albert

Les 50 fiches préparées restent utilisables ; leurs propositions sont complétées par des savoir-faire ROME pertinents selon les priorités officielles. Le boulanger conserve ses 13 propositions relues. Pour les autres métiers, Albert peut choisir 1 à 8 savoir-faire uniquement parmi les relations vérifiées du métier commun. Aucun identifiant absent ni savoir-être généré librement n’est accepté.

Le cache PostgreSQL existant est partagé entre candidat et employeur, indexé par métier canonique, version des sources et méthode/modèle (simulation distincte). La transaction est relâchée pendant l’appel externe ; un bail empêche une réponse ancienne de remplacer une réponse plus récente. Les réponses en cache sont revalidées. Un échec ou un appel déjà en cours laisse une liste de référence utilisable, sans nouvel appel immédiat. Sans configuration Albert, une sélection déterministe issue des priorités officielles reste disponible ; ce n’est pas une simulation d’IA.

L’interface ne présélectionne aucune compétence. Cinq compétences et trois savoir-être maximum par métier sont contrôlés côté navigateur et serveur. Les sélections existantes, toujours valides dans les sources, sont conservées même si la liste courte change. Les métadonnées reçues du navigateur ne font pas autorité : provenance, versions et correspondances sont reconstruites au serveur.

## Conservation et matching

Le profil candidat et l’offre utilisent leurs champs JSON existants, sans migration. Les références historiques restent acceptées. Les alias d’un même métier partagent un compteur et ne deviennent pas deux exigences alternatives. Le choix d’un métier reste distinct de la possession d’une compétence.

Le matching rapproche seulement les identifiants de compétences réellement déclarés. Une correspondance entre métiers, une ressemblance de libellés ou une source éditoriale ne crée aucune équivalence entre compétences. Une compétence non déclarée reste à vérifier, jamais automatiquement absente. Les nouveaux libellés ROME et ESCO sont visibles dans les explications conseiller. Poids, décisions humaines et droits ne changent pas ; version du calcul identifiée comme `common-reference-v2`.

## Construire et vérifier

- `make common-source-build CATALOG_SOURCES=/chemin/exports-esco ROME_DEFINITIONS_ARCHIVE=/chemin/rome.zip` : archives officielles épinglées, reconstruction hors ligne de la ressource portable. Une autre empreinte est refusée.
- `make common-source-audit` : vérifier chaque tranche, les identifiants et la présence de savoir-faire.
- `make test TESTS="tests.skills.test_common_catalogue tests.matching.test_common_skills"` : regroupements exacts, ambiguïtés, cache, réponses invalides, droits, sauvegardes et matching.
- `make test` : suite complète sur la base de test PostgreSQL propre au worktree. Exécutions séquentielles sur cette même base.
- `make check`, `make check-js`, `make translations-check` : contrôles structurels.
- `make run PORT=9046` : essai sur le port 9046 ; désactiver les e-mails et les appels Albert réels dans le `.env` de test.

Les comptes de test restent explicitement fictifs. La recette navigateur a vérifié le choix 5+3, sa conservation côté candidat pour Chef boulanger, la même liste côté employeur et l’enregistrement du brouillon fictif. Une fiche agricole regroupée hors du premier pilote a aussi été ouverte avec ses compétences des deux sources. Cette recette initiale n’a utilisé aucun appel Albert réel ni envoyé de message utilisateur.

## Validation initiale avant adaptation à la pile

- Suite complète PostgreSQL : 618 tests réussis (journal local `.runtime/common-suite-final.log`).
- Contrôles ciblés catalogue/cache/matching : 14 tests réussis après les derniers ajustements de lecture.
- Audit hors ligne : 4 962 fiches source, 192 911 relations, 32 029 identifiants ; aucune fiche sans savoir-faire.
- Django : contrôles structurels et absence de migration. Traductions d’interface FR/EN/DE contrôlées et compilées. JavaScript vérifié et formaté.
- Recette navigateur : fiche agricole exacte commune, choix issus des deux sources, limites 5+3 et conservation après navigation ; fiche Chef boulanger indépendante, même liste côté employeur et brouillon fictif enregistré. Rendu allemand vérifié, avec libellés ROME non traduits conservés en français et marqués dans le bon langage HTML.
- Le libellé français ambigu du pétrissage est corrigé par une aide de lecture identifiée dans le code, sans modifier les identifiants ni les octets des sources officielles ; le cache distingue cette méthode de lecture.
- Aucun appel réel à Albert n’a été testé : appels simulés par les tests et propositions de référence disponibles dans l’essai local. Aucune fusion ni opération de production.

## Validation sur le sommet de pile

Après adaptation à l’organisation actuelle (`www`, tests centralisés et client Albert commun),
la suite PostgreSQL exécute 847 tests sans échec, dont huit contrôles HTML réservés
à l’environnement qualité et exécutés séparément avec succès. Les 41 tests JavaScript
passent. Contrôles Django/migrations, budgets documentaires, Black, HTML, CSS, JS et
gettext réussis ; audit des 4 962 fiches source inchangé. Aucun appel Albert réel,
fusion ni déploiement. La recette visuelle initiale n’est pas présentée comme
un nouveau contrôle sur téléphone après adaptation.
