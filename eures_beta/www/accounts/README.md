# Interface accounts

Connexion, déconnexion, compte et orientation vers le tableau de bord du rôle connecté.

[Retour à la couche web](../) · [Architecture](../../../docs/ARCHITECTURE_WEB.md)

## Fichiers

- [__init__.py](__init__.py) — Déclare le paquet Python, sans modèle ni effet au chargement.
- [forms.py](forms.py) — Définit et valide les formulaires propres aux écrans de ce parcours.
- [return_path.py](return_path.py) — Reprend l’import employeur ou le dialogue candidat uniquement pour le rôle connecté compatible, sinon revient au tableau de bord ; les droits sur l’offre restent vérifiés à l’arrivée.
- [test_accounts.py](test_accounts.py) — Expose les comptes fictifs uniquement dans les environnements explicitement autorisés.
- [urls.py](urls.py) — Associe les URL existantes aux vues, sans changer leur nom public.
- [views.py](views.py) — Traite les requêtes de ce parcours et prépare les réponses.

Les routes de compte restent sous `/accounts/` ; la relecture conseiller est désormais `/matching/<id>/review/`.

Le suivi des confirmations quitte le tableau de bord technique : il utilise
`/matching/offer-reviews/<id>/`, sans changement de la vue conseiller.

Le planning des conseillers est accessible via la route nommée `adviser_planning` sous `/adviser/planning/`.
