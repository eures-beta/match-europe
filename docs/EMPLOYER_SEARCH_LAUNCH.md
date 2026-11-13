# Recherche de candidats : retrait du simulateur historique

Les routes de lancement et de vérification du simulateur employeur ainsi que
son formulaire de scénarios sont retirés. Aucune recherche ou prise de contact
externe ne peut être déclenchée par ces anciens accès.

Les modèles `EmployerSearchOperation` et `EmployerSearchEvent` sont retirés,
avec leurs tables et leur administration. La migration `employers.0007` refuse
le retrait si elle trouve encore une ligne dans ces tables ou celle des anciens
liens employeurs : les données doivent alors être examinées séparément.

Les offres restent conservées. Leur date `search_started_at` continue de
verrouiller une recherche déjà démarrée ; la duplication produit une copie
modifiable. Les états pending/uncertain du simulateur n'existent plus.

Le rapprochement actuel relève du [matching](MATCHING.md) et de l'espace
conseiller ; il ne constitue pas un lancement automatique de qualification AGLAE.
`make test-retired-paths` vérifie l'absence des anciennes routes.

`make retired-models-test` vérifie la suppression sur tables vides, le refus
sur données existantes, la préservation des comptes/offres et le retour arrière.
Le rollback recrée les tables vides ; il ne restaure aucune donnée supprimée.
