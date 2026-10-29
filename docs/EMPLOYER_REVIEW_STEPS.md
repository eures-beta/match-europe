# Relecture du dépôt d’offre en cinq étapes

Le parcours employeur après import ou saisie est réparti en poste, conditions,
profil, mobilité et récapitulatif. Les contrôles existants sont déplacés sans
changer leurs identifiants ni dupliquer leurs valeurs. Le bouton Continuer
contrôle l’étape visible ; Précédent et Modifier depuis la synthèse conservent
les réponses. L’enregistrement reste disponible seulement à la dernière étape.
Les informations facultatives restent signalées ; les choix À préciser sont
explicites lorsque proposés. Aucune autosauvegarde n’est ajoutée.

## Conditions et langues

La rémunération distingue montant/fourchette, devise, brut/net et période ;
la durée indique les heures hebdomadaires fixes ou variables. Les contraintes
horaires, dont Horaires avec coupure, sont dans les conditions de travail avec
une précision facultative. La prise de poste accepte dès que possible, une date
précise ou une date flexible. Les données importées non reconnues restent
conservées au lieu d’être interprétées silencieusement.

Le module langues affiche uniquement les langues retenues, avec ajout depuis
une recherche locale ISO 639-1 et libellés du navigateur via Intl.DisplayNames.
Les alias FR/EN/DE évitent les doublons de nom. Chaque langue a un niveau A1–C2
expliqué, modifiable, et une action Retirer. L’alternative explicite Aucune
exigence linguistique particulière est exclusive de la liste. Un niveau n’est
prérempli que si un couple langue/niveau explicite est reconnu. Le texte ambigu
est préservé ; les langues absentes ne sont pas assimilées à des réponses négatives.
Les descripteurs sont des repères pratiques inspirés de l’échelle globale CECR,
pas une certification ni un test de langue.

## Limites et compatibilité

Ce lot améliore l’interface du prototype et réutilise le contrat de sauvegarde
existant. Les valeurs guidées sont sérialisées dans les clarifications textuelles ;
un schéma métier structuré et sa validation serveur restent à traiter. Les
contrôles ajoutés de complétude et de fourchettes sont dans le navigateur ; les
contrôles serveur existants restent applicables. La condition split est ajoutée
aux valeurs autorisées côté serveur et à l’éditeur historique pour la conserver.
Aucune migration, nouvelle dépendance ou intégration externe. Le contact reste
un formulaire séparé, accessible à la dernière étape et enregistré séparément.
Le parcours candidat n’est pas modifié.

Les cinq étapes concernent import.html ; import-v2.html reçoit seulement le
choix coupure pour conserver la cohérence des conditions. Les règles visuelles
existantes et les assets officiels EURES sont conservés. Navigation et textes
existent en FR/EN/DE ; le focus est déplacé vers le titre de l’étape affichée.

## Vérification fonctionnelle locale

Données fictives : navigation aller/retour, modification depuis le récapitulatif,
blocage sans réponse et enregistrement final puis reprise. Rémunération
2400 EUR brut mensuel, durée 35 heures, début dès que possible ; fourchette
inversée refusée, fourchette valide acceptée. Préremplissage French: A1 ; ajout
anglais B1, sauvegarde et reprise ; retrait des langues bloquant la progression,
puis réponse sans exigence autorisant la suite. Case coupure et exclusion de
Aucune condition particulière vérifiées. Une recette locale ne constitue pas
une validation d’exploitation ni une autorisation de déploiement.
