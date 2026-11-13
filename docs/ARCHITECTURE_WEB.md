# Séparer interfaces web et domaines métier

L’organisation distingue deux responsabilités, sur le modèle de `itou/www`
dans Les emplois. Le nom `www` est un rangement Python : il n’ajoute ni site,
ni sous-domaine, ni préfixe aux URL.

| Emplacement | Responsabilité |
| --- | --- |
| `eures_beta/www/` | Routes, vues, formulaires d’écran et orchestration HTTP par parcours |
| `eures_beta/users/` | Comptes, authentification et règles communes associées |
| `eures_beta/invitations/` | Modèle, services, autorisations et administration des invitations |
| `eures_beta/employers/` | Offres, établissements, propriété, lecture et validation des offres |
| `eures_beta/candidates/` | Profil, inscription, brouillons et validation partagée du questionnaire |
| `eures_beta/matching/` | Calculs, évaluations, décisions, confirmations et conversations |
| `eures_beta/occupations/` et `skills/` | Catalogues, recherche et services de compétences |
| `eures_beta/templates/`, `static/`, `locale/` | Ressources partagées de présentation et traductions |
| `tests/` | Tests centralisés par domaine, y compris ceux des interfaces |

Les vues importent les modèles et services. Les domaines ne doivent pas importer
`www` : leurs règles sont également nécessaires aux commandes, aux modèles et
aux intégrations sans requête HTTP. Le questionnaire candidat conserve donc ses
formulaires de validation partagés dans `candidates/forms.py`. Les choix des
habitudes de réponse restent dans `employers/response_practice.py`, et la validation
des offres dans `employers/offer_validation.py`. La disponibilité des emails de
connexion reste dans `users/email_login.py` pour l’inscription et la connexion.

Les paquets web ne sont pas enregistrés comme nouvelles applications Django.
Les applications qui possèdent les modèles, leurs labels, migrations, tables,
permissions et ContentTypes ne changent pas. Aucun déplacement de données ni
nouvelle migration ne sont nécessaires. Les anciens modules Python sont retirés,
sans alias de compatibilité ; les imports, mocks et routes utilisent leurs
nouveaux emplacements. Les adresses et noms de routes publics restent identiques.

Pour ajouter une page, choisir son parcours dans `www`, puis appeler les services
du domaine concerné. Un écran peut utiliser plusieurs domaines. Ne pas déplacer
une règle de validation partagée dans une vue pour éviter un import supplémentaire.
Les helpers prenant une requête ou une session et les formulaires propres aux
écrans appartiennent à la couche web. Les emails et services externes conservent
leurs frontières et protections existantes.

## Vérification

```bash
make test
make check
make e2e-test
```

Les contrôles d’architecture sont dans
[test_web_architecture.py](../tests/common/test_web_architecture.py).
Ils refusent les imports de la couche web depuis les domaines et vérifient que
les routes applicatives pointent vers les adaptateurs web. Les routes natives
Django (administration, traduction et redirections) et la sonde restent distinctes.

[Couche web](../eures_beta/www/) · [Retour à la documentation](./)
