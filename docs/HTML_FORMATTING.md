# Format des templates Django

Black formate Python ; djLint formate les templates HTML Django.
Installer les outils avec `make install-quality`, puis lancer `make format-html`.
`make format-html-check` vérifie le résultat sans modifier les fichiers.

Indentation : deux espaces ; longueur cible : 120 caractères. Les expressions
de template et certains attributs indivisibles peuvent dépasser cette cible.
Le JavaScript externe n’est pas reformaté par cette commande.

GitHub Actions vérifie les push et les PR. Un écart produit un contrôle rouge ;
aucune correction automatique ni règle de fusion obligatoire n’est ajoutée.
