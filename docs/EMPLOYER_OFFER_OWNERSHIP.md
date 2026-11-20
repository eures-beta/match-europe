# Propriété des offres employeur

Chaque offre appartient à son compte employeur `JobOffer.created_by`. Un compte
employeur actif consulte, modifie et duplique uniquement ses propres offres.
Le nom d’entreprise (`data.companyName`), le contact et les paramètres d’URL ne
donnent aucun droit. Les offres sans propriétaire ne peuvent pas être réclamées
par une session de navigateur ou une adresse e-mail correspondante.

Le parcours actuel est : invitation du compte, connexion, import/relecture,
enregistrement avec propriétaire, puis tableau de bord. Aucun établissement,
adhésion ou rattachement supplémentaire n’est nécessaire. L’ancien accès
`/employer/offers/` rend le même tableau de bord ; ses détails et actions gardent
les contrôles de rôle, propriété, CSRF, révision et verrou de recherche.
Les anciennes actions de rattachement répondent 410 sans modifier de données.

## Données et migration

La migration `employers.0009_remove_company_workspaces` supprime `Company`,
`CompanyMembership` et la relation `JobOffer.company`, pas les comptes ou offres.
Elle conserve leurs UUID, créateurs, contacts, données extraites et noms affichés.
Elle refuse une offre liée à un établissement sans propriétaire employeur valide :
aucune attribution implicite ne doit remplacer une décision humaine.
Les adhésions et établissements sont supprimés ; un retour de schéma ne restaure
pas leurs anciennes données. Les migrations historiques restent immuables.

Le matching des offres complètes utilise le compte employeur actif, les champs
requis, la révision des copies et l’état de validation, sans relation établissement.
Aucun calcul global n’est déclenché par la migration. Les empreintes existantes
conservent leurs clés vides historiques pour les offres sans établissement :
les confirmations déjà enregistrées ne sont pas invalidées par un renommage technique.

## Vérification

`make test TESTS=tests.employers` couvre l’isolation entre comptes, les sessions,
les contacts distincts, les refus d’accès et la migration sur offres non vides.
Les tests historiques continuent à vérifier les anciennes transitions du schéma.
