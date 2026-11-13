# Client Albert partagé

Les trois usages passent par `eures_beta/integrations/albert.py::complete_json` :
structuration des offres, sélection de compétences ESCO et dialogue candidat.
Les applications métier ne reconstruisent plus de requête HTTP Albert.

Le client commun possède l’URL HTTPS fixe, l’authentification par `ALBERT_API_KEY`,
le refus des redirections, le format JSON sans streaming, les lectures bornées,
le contrôle de durée et les erreurs sans contenu sensible du fournisseur.
Il n’expose aucun outil ni écriture en base au modèle.

Les prompts, listes de champs autorisés, preuves textuelles, validations Django,
contrôles d’accès, simulations et caches restent dans les applications métier.
Mutualiser le transport ne change pas ces règles et ne donne aucun nouveau droit.

## Budgets préservés

`Limits` est une configuration Python immuable propre à chaque appelant. Elle
permet de partager le transport sans élargir les limites du dialogue ou des
compétences pour les aligner sur celles de l’import.

| Usage | Délai réseau | Budget durée contrôlé après lecture | Réponse maximale | Requête maximale | Tokens |
| --- | --- | --- | --- | --- | --- |
| Offre PDF/texte | 35 s | 40 s | 100 000 octets | Validation métier existante | 3 500 |
| Dialogue candidat | 25 s | 30 s | 20 000 octets | 24 000 octets | 1 800 |
| Compétences ESCO | 35 s | 40 s | 30 000 octets | 180 000 octets | 2 000 |

L’import et les compétences utilisent `ALBERT_MODEL`. Le dialogue conserve
`ALBERT_DIALOGUE_MODEL`, transmis explicitement au client partagé. L’import garde
sa tolérance historique aux délimiteurs Markdown autour du JSON ; le dialogue
et les compétences continuent à exiger du JSON sans ces délimiteurs.

Aucun nouveau secret, paramètre d’environnement, modèle ou migration n’est
nécessaire. La sélection du modèle reste une configuration de l’application,
jamais une URL libre fournie par l’utilisateur.

## Vérifications

`make test` couvre les trois usages avec une réponse réseau simulée au niveau du
client commun. Le paramètre existant `TEST_ARGS='-k albert'` permet de sélectionner
les tests Albert lors d’une itération ciblée, sans ajouter de cible Makefile.
Les tests métier
continuent à vérifier les prompts, preuves et sorties autorisées. Les tests du
client couvrent aussi les budgets, le modèle choisi, le refus avant appel d’une
requête trop grande et les erreurs de réponse/durée. Aucun appel Albert réel.

`make test check` vérifie la suite PostgreSQL et la cohérence Django/migrations.
