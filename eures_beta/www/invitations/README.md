# Interface invitations

Acceptation et préparation des invitations ; les comptes et invitations restent dans leur domaine métier.

[Retour à la couche web](../) · [Architecture](../../../docs/ARCHITECTURE_WEB.md)

## Fichiers

- [__init__.py](__init__.py) — Déclare le paquet Python, sans modèle ni effet au chargement.
- [adviser.py](adviser.py) — Prépare, prévisualise et suit les invitations depuis le parcours conseiller.
- [forms.py](forms.py) — Définit et valide les formulaires propres aux écrans de ce parcours.
- [urls.py](urls.py) — Associe les URL existantes aux vues, sans changer leur nom public.
- [views.py](views.py) — Traite les requêtes de ce parcours et prépare les réponses.

Le conseiller prépare et suit les invitations sous `/adviser/invitations/` et `/adviser/invitations/new/`. L’acceptation commune reste `/accounts/invitations/confirm/`.
