# Accueil candidat — écran 1

L’entrée `/forms/eures-beta/candidate?lang=fr` ouvre directement le premier écran,
avec CV, lien LinkedIn ou saisie manuelle. FR, EN et DE sont disponibles. Toute
autre langue explicite revient au français. La racine reste l’accueil employeur.

L’écran reprend la coque employeur, ses logos intégraux et ses styles. Les choix
reprennent le modèle de l’import employeur : bloc cliquable, repère, texte Arial
et flèche. Les fichiers institutionnels existants sont réutilisés sans copie
supplémentaire ni retouche. Aucune nouvelle certification de marque ou WCAG
n’est revendiquée.

## Sources et génération

`candidate-copy.json` centralise les textes FR/EN/DE suivant la convention des
prévisualisations existantes. `build-candidate.cjs` reprend les pages employeur
générées et crée les trois pages `candidate-fr.html`, `candidate-en.html` et
`candidate-de.html`. `candidate.css` et `candidate.js` restent propres au candidat.

Depuis la racine :

```sh
node previews/employer-landing/build-candidate.cjs
```

La génération employeur complète appelle également ce générateur en dernier.
Les vues Django restent soumises à la restriction de démonstration existante et
n’acceptent que GET/HEAD. Aucun changement de modèle ni migration PostgreSQL.

## Essai et limites

Sur le serveur Django local configuré avec `ME_EMPLOYER_LOCAL_API=1`, ouvrir
`/forms/eures-beta/candidate?lang=fr`. Changer de langue, parcourir les boutons au
clavier et activer chaque choix. Chaque clic affiche une limite explicite sans
quitter l’écran. Le bouton de connexion indique également que cette étape reste
à préparer ; il n’ouvre pas la connexion employeur.

Aucun formulaire, upload, consultation LinkedIn, stockage navigateur, création
de profil, contact ou appel externe. Les encarts décrivent le parcours cible.
La suite et l’authentification candidat restent à définir et à raccorder.
Les autres liens de la coque conservent leur comportement historique.

Vérifications : quatre tests Django sans base couvrent la langue et les
redirections, la séparation de l’API employeur, les ressources autorisées et les
restrictions de méthode/démonstration. Contrôles navigateur FR/EN/DE, logos,
absence de débordement à la largeur observée et activation clavier effectués.
Cette validation ne constitue pas une recette complète du parcours candidat.
