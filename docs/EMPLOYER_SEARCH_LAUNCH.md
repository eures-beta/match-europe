# Recherche de candidats : retrait du simulateur historique

Les routes de lancement et de vérification du simulateur employeur ainsi que
son formulaire de scénarios sont retirés. Aucune recherche ou prise de contact
externe ne peut être déclenchée par ces anciens accès.

Les offres et les opérations historiques restent conservées. Un ancien état de
recherche en cours ou incertain conserve son verrouillage : le retrait de l'écran
ne rend pas une offre verrouillée modifiable. La duplication reste possible.

Le rapprochement actuel relève du [matching](LOCAL_MATCHING.md) et de l'espace
conseiller ; il ne constitue pas un lancement automatique de qualification AGLAE.
`make test-retired-paths` vérifie l'absence des anciennes routes.
