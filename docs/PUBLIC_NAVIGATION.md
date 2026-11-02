# Navigation publique

Les menus utilisent les noms de routes Django : accueil à `/`, candidat à
`/candidate/`, statistiques à `/statistics/`, projet à `/project/` et journal à
`/journal/`. Les statistiques et le journal affichent une annonce « en construction »
en FR/EN/DE, avec retour à l’accueil et choix de langue. La page Projet reprend
le contenu éditorial historique en FR/EN/DE, dans un template Django/gettext,
avec sommaire et quinze sections. Ces pages ne collectent aucune donnée.

Les anciennes adresses des formulaires sont déclarées uniquement dans les routes
de compatibilité. Django `RedirectView` les redirige en HTTP 301 vers les routes
canoniques, en préservant la chaîne de requête. Seules les lectures GET/HEAD sont
acceptées ; aucune écriture n’est redirigée. Les contrôles d’accès du parcours
candidat restent appliqués à destination.

Les redirections historiques des pages employeur restent limitées à la liste
existante des anciennes pages autorisées. Les routes métier employeur et les
versions d’import ne sont pas supprimées dans ce nettoyage.

La racine appartient uniquement à l’accueil. Les anciens parcours de `/access/`
et `/dashboard/` sont retirés ; ils répondent 404.

Vérifications : `make test`, `make check`, `make format-check`,
`make format-html-check`, `make format-js-check`, `make check-js` et
`make translations-check`.

Les pages d’attente et l’accueil partagent public_base.html : navigation active,
logos partenaires et pied de page. Le bloc de marque (logo Match Europe et
sous-titre traduit) est commun aux en-têtes publics et métiers, avec ses styles
dans public-brand.css. Les tests vérifient sa présence identique dans chaque
onglet et chaque langue.

## Page Projet — reprise du 2 novembre 2026

Source relue : [page Projet historique](https://matcheurope.beta.francetravail.fr/forms/eures-beta/le-projet?lang=fr),
textes FR/EN/DE servis par son fichier JavaScript public à cette date. La page
Django ne charge pas ce script : son contenu est rendu côté serveur, avec les
liens candidat/employeur actuels, les logos et le cadre public existants.
L’exemple fictif, les réserves sur les chiffres à consolider, l’horizon indicatif
de candidats et le canal WhatsApp seulement envisagé sont conservés. Le texte
présente le projet et ses expérimentations historiques ; cette reprise éditoriale
ne confirme ni la disponibilité actuelle de chaque parcours ni ces résultats.

Vérification de reprise : tous les textes des quinze sections ont été retrouvés
dans les réponses HTML locales de chaque langue, sommaire et réserves compris.
Tests de régression inclus dans `make test` : contenu trilingue, liens d’ancrage,
langue invalide, accès public hors démo et méthodes GET/HEAD uniquement.
