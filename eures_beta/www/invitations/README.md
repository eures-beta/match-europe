# Interface invitations

Acceptation et préparation des invitations ; les comptes et invitations restent dans leur domaine métier.

[Retour à la couche web](../) · [Architecture](../../../docs/ARCHITECTURE_WEB.md)

## Fichiers

- [__init__.py](__init__.py) — Déclare le paquet Python, sans modèle ni effet au chargement.
- [adviser.py](adviser.py) — Prépare, prévisualise et suit les invitations sans quota horaire ni plafond de lignes CSV ; contrôle les relances à 24 heures et annonce le résultat par destinataire depuis le parcours conseiller ; réutilise le contexte visuel et les logos du [rendu commun](../../emails/).
- [forms.py](forms.py) — Définit et valide les formulaires propres aux écrans de ce parcours.
- [urls.py](urls.py) — Associe les URL existantes aux vues, sans changer leur nom public.
- [views.py](views.py) — Traite les requêtes de ce parcours et prépare les réponses ; le libellé d’action de l’e-mail est traduit au rendu dans la langue du destinataire.

Le conseiller prépare et suit les invitations sous `/adviser/invitations/` et `/adviser/invitations/new/`. L’acceptation commune reste `/accounts/invitations/confirm/`.
