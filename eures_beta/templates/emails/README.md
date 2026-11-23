# Présentation e-mail commune

- [base.html](base.html) : carte, typographie, en-tête et pied de page partagés,
  repris du design des invitations employeur ; logos partenaires inchangés.
- [action.html](action.html) : bouton principal commun avec un vrai lien HTML.
- [message.html](message.html) : contenu transactionnel échappé, titre et action
  facultative dans le gabarit commun.
- [link_fallback.html](link_fallback.html) : adresse complète à copier dans les
  invitations riches, avec retour visuel à la ligne sans modifier l'adresse.

Les templates métier étendent `base.html` et fournissent leur contenu ; ne pas
recopier une carte ou un pied de page par parcours. Les valeurs visuelles communes
sont centralisées ici, avec des styles intégrés compatibles e-mail. Ces quatre
fichiers ont une exception d'attributs `style`, sans autoriser les blocs `<style>`.

Le texte métier et gettext restent partagés ; aucun script ni ressource externe
n'est nécessaire pour activer un lien ; les logos sont facultatifs pour la lecture.
Voir le [rendu](../../emails/) et
[l'étude de compatibilité](../../../docs/EMAIL_LINKS.md).
