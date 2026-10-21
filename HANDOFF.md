# Reprise du prototype Match Europe

## Entrée employeur — 23 octobre 2026

À la demande d’Eric, `/` redirige temporairement (302) vers
`/previews/employer-landing/fr.html`. Les pages EN/DE restent accessibles par
le sélecteur existant. `/access/` conserve les comptes de démonstration et
`/dashboard/` conserve la navigation des quatre rôles après connexion.
Aucun changement graphique, de données ou de service externe.
Validation : 76 tests PostgreSQL passent, dont redirection HTTPS, accueil
FR/EN/DE, accès aux rôles et navigation privée ; `git diff --check` réussi.

## Adaptation de recette — 23 octobre 2026

Autorisation utilisateur distincte : rebaser la PR #2 sur `main`, résoudre les
conflits et ajouter les adaptations dans des commits propres à l’agent, puis
pousser la branche. L’utilisateur ajoutera lui-même le label d’une semaine.
Aucune fusion ni activation du label par l’agent n’est prévue.

Le point d’entrée racine sélectionne désormais les parcours conservés, avec la
sonde PostgreSQL et les statiques du socle. Le mode partagé HTTPS conserve les
protections CSRF/session et initialise seulement une base de démonstration neuve.
Les enregistrements AGLAE et le diagnostic Push sont désactivés. Le lanceur
autonome reste disponible. Voir le README racine pour les commandes et limites.

Vérifications locales : 74 tests du point d’entrée racine et 59 tests du prototype
autonome passent sur PostgreSQL. Migrations et collecte des statiques réussies ;
essai Gunicorn avec rôles fictifs, accès et pages employeur FR/EN/DE à 200,
statiques à 200, santé PostgreSQL à 204, diagnostic Push refusé (404).
Le déploiement de cette adaptation reste à vérifier après le label humain.
## 21 octobre 2026 — parcours employeur avant email

Branche `codex/employer-offer-creation`, basée sur la branche de la PR nº 2. Lecture PDF/URL/texte, vérification et correction avant collecte de l’email et du contact ; demande de lecture portée par le clic sans case supplémentaire. Corrections validées côté serveur lors de l’enregistrement. Textes FR/EN/DE ; mention technique retirée du contact. Les améliorations du lecteur PDF de la PR nº 14 et le changement de logo sont exclus. Mode de recette local sans services externes (`ME_LOCAL_REVIEW_ONLY=1`). Aucun merge ni déploiement autorisé.

La recette précédente avec lecteur amélioré comptait 75 tests ; cette branche indépendante passe 61 tests PostgreSQL, dont les deux nouveaux tests de parcours. Syntaxe des trois scripts JS et diff vérifiés. Les documents et coordonnées de recette sont fictifs et restent hors Git.

## Partage initial — 16 octobre 2026

Cette branche importe une photographie du prototype local, extraite du checkout historique au commit de base `d64f88cd5cbc260c8249cd9ba3842158bc876247` avec ses fichiers de prototype alors non suivis. Aucune réécriture de l’historique du dépôt historique ni copie de sa base locale.

Périmètre : TRANSVERSE, avec les quatre volets EMPLOYEURS, CANDIDATS, CONSEILLERS et ADMIN. Références : [vue d’ensemble](docs/VUE_ENSEMBLE.md), [décisions](docs/DECISIONS.md), [guide de revue](docs/PROTOTYPE_REVIEW.md).

- La V2 employeur est la référence UX acceptée. V1 reste disponible pour comparaison.
- L’import employeur et le modèle `EmployerImport` restent distincts des `Offer` du parcours de matching fictif.
- Le contact entreprise est stocké séparément, avec contrôle d’accès par session et rôle ; attribution conseiller faite par l’admin.
- Les questions de préqualification de la V2 sont momentanément masquées ; aucune exclusion automatique.
- Une conversation métier correspond à un couple candidat–offre après accords et intervention du conseiller.
- Les notifications de test sont isolées. Leur réception a été confirmée manuellement sur le Mac du testeur, mais aucun résultat multi-appareil ou production n’est acquis.

Le dépôt ne contient pas les secrets, données PostgreSQL, abonnements, sessions, documents déposés, sauvegardes locales de versions ni procédures privées d’hébergement.

## À reprendre ensuite

1. Relire les commits par thème ; extraire ensuite de petites PR destinées à une fusion éventuelle.
2. Consolider les templates Django, la génération V2, les traductions et les styles.
3. Raccorder les imports au vrai modèle métier et les notifications au bon participant avec ses droits.
4. Définir authentification de production, révocation, conservation, accords et notices validées.
5. Réaliser audits sécurité, accessibilité et marque ; préparer seulement ensuite un périmètre de recette externe.

Aucun merge ou déploiement n’est autorisé par cette PR. La branche principale doit rester inchangée.

## Vérifications effectuées pour ce partage

Dans ce nouveau clone, avec son propre environnement virtuel et une nouvelle instance PostgreSQL locale :

- Initialisation et migrations `0001` à `0004` : réussies.
- Chargement idempotent des quatre rôles fictifs : réussi.
- `manage.py test journeys --noinput` : **59 tests passent** ; services externes mockés.
- `manage.py check` : aucun problème signalé.
- `makemigrations --check --dry-run` : aucun changement détecté.
- Syntaxe Node des huit fichiers JS/CJS de prévisualisation et JSON : validés.
- HTTP local `/access/`, `/static/app.css`, `/static/bootstrap.min.css` : 200.
- Contrôle des formats de secrets et recherche des secrets locaux connus : aucun dans le jeu de publication.

Les alertes 400/404/409/502 dans la sortie des tests correspondent aux scénarios négatifs attendus. Aucun appel réel au prestataire, géocodeur ou service Push n’a été réalisé pendant cette validation de publication. Une première exécution de tests pendant l’assemblage des commits intermédiaires n’avait pas les routes Push ; la validation ci-dessus porte sur l’état final avec ces routes présentes.
