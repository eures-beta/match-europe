# Guide de lecture — PR de conservation du premier prototype

Cette PR sert à partager et conserver le travail exploratoire. Ne pas fusionner ou déployer en bloc. Les commits offrent des groupes de lecture ; ils ne prétendent pas reconstituer chronologiquement les conversations ou fournir des versions intermédiaires toutes exécutables.

## Ordre de lecture

1. **Configuration** : Django, PostgreSQL local, paramètres explicites, runtime ignoré.
2. **Domaine** : modèles, migrations additives, services, formulaires, PDF isolé, identités fictives.
3. **Parcours** : droits, vues, quatre tableaux de bord, traduction et conversation.
4. **Import et contact employeur** : sources publiques/PDF, session, anti-SSRF, révisions, sandbox inactive, affectation conseiller/admin.
5. **Interface employeur** : V1 et référence V2 FR/EN/DE, logos et ressources historiques de présentation.
6. **Diagnostic Web Push** : boucle locale uniquement, demande d’autorisation explicite, abonnements en session, notification générique.
7. **Documentation et validation** : limites, commandes, résultats observés et provenance.

## Pourquoi conserver certains fichiers hérités ?

`forms/eures-beta/app.js` et `site.css` sont copiés depuis le dépôt EURES beta pour reproduire et générer les maquettes employeur. Aucun module Flask ni dépendance Grist n’est importé. Les routes de navigation historiques ne constituent pas des parcours complets dans ce dépôt ; seule la feuille CSS dispose d’une route de compatibilité. Ces deux fichiers doivent être remplacés progressivement par des templates et ressources propres à Match Europe.

`build.cjs` génère la landing, les notices et la V1. La V2 contient encore des modifications directes de HTML généré ; lancer le générateur ne régénère pas toutes ces modifications. Conserver les HTML V2 comme source de la proposition retenue jusqu’à consolidation. Les archives de retouches locales ne sont pas publiées ; les sources originales restent dans le checkout initial.

`aglae-offer-snapshot.json` est une copie expurgée d’une annonce publique utilisée comme exemple statique. Ce n’est ni une donnée candidate, ni un secret, ni le mécanisme du parcours relié au serveur. Les tests automatisés emploient des données fictives et des mocks réseau.

## Points de vigilance connus

- Mode démo et accès de rôle partagés incompatibles avec de vraies données personnelles.
- Pas d’email réel ; la possession d’une session de brouillon ne vaut pas authentification de production.
- Parsing textuel et sources publiques non contractuelles ; pas d’OCR ni analyse IA sémantique des documents dans le lecteur.
- AGLAE sandbox est opt-in, offres inactives seulement, pas de matching ou qualification automatique.
- Diagnostic Web Push séparé du métier ; envoi différé en mémoire non durable, page technique francophone.
- Notice historique signalée comme non validée pour le nouveau traitement.
- Génération et styles à consolider ; conformité complète FR/EN/DE, WCAG et marque non certifiée.

## Provenance des ressources

Les logos EURES/ELA, France Travail, ADEM et Le Forem sont copiés sans redessin depuis les ressources locales du projet historique. La signature nominative Forem n’est pas incluse. Bootstrap conserve son en-tête de licence MIT. Les documents de marque privés et les procédures d’hébergement FT ne sont pas publiés.
