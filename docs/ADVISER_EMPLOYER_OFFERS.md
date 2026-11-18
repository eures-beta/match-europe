# Consultation des offres employeur

Dans l’espace conseiller, ouvrir **Données et historique → Offres employeur**.
Le paramètre existant `view=employers` est conservé.

La liste affiche toutes les `JobOffer` enregistrées, comme la liste administrative :
la date de validation, le rattachement à un établissement, l’activité ou la présence
du créateur ne sont pas des conditions de visibilité. Ce choix concerne uniquement
la consultation par les conseillers connectés et actifs. Il ne valide aucune offre,
ne lance aucune recherche et ne modifie pas les sélections du matching.

La liste est triée par date de création décroissante, paginée par 20 et recherchable
par titre, entreprise, établissement, lieu, e-mail du dépôt ou du créateur.
Cliquer sur le titre ouvre les coordonnées du contact, les réponses de l’offre,
les références métier et compétences, les questions candidat, les exigences de
matching explicitement enregistrées et le suivi des dates/origine/révision.
L’en-tête met en avant entreprise, poste, lieu et statut. Les informations sont
présentées en deux colonnes, les textes longs en pleine largeur et le suivi
technique reste repliable. Une valeur absente reste signalée discrètement. Les codes de choix sont traduits ; le texte
saisi par l’employeur n’est pas traduit automatiquement.

Les secrets de session et les réponses techniques externes ne sont pas exposés.
L’URL source est affichée comme texte avec le masquage commun des paramètres
sensibles. Les textes employeur sont échappés. Aucun droit Django Admin n’est
nécessaire ni accordé. Candidats, employeurs, comptes inactifs et visiteurs ne
peuvent pas consulter cette rubrique. Aucun POST ni modification de données métier.

Vérifications : `make test TESTS=tests.users.test_adviser_history`, puis `make test`.
Contrôles : `make check`, `make format-check`, `make format-html-check`,
`make format-css-check` et `make translations-check`. Recette locale avec les
comptes fictifs documentés dans [TEST_ACCOUNTS.md](TEST_ACCOUNTS.md), liste et
détail à vérifier en français, anglais et allemand ; sur petit écran, la liste
défile horizontalement dans sa région et le détail passe en une colonne.
