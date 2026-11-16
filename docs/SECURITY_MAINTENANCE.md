# Maintenance des dépendances et détection de secrets

Dependabot lit `.github/dependabot.yml` depuis la branche par défaut après sa
fusion. Chaque lundi à 07 h, heure de Bruxelles, il recherche les mises à jour
Python (dont Django), npm et GitHub Actions. Les versions mineures/correctives
ordinaires sont regroupées par écosystème ; les versions majeures Python/npm
restent séparées. Trois PR de versions au maximum sont ouvertes par écosystème.
Les corrections de vulnérabilités dépendent des alertes et mises à jour de
sécurité activées dans les paramètres GitHub ; elles ne sont pas limitées au
rendez-vous hebdomadaire. Aucune fusion automatique n’est configurée.

Le Dockerfile du banc E2E est également suivi, même si son dossier est déplacé.
Dependabot peut actualiser l’image Python épinglée par digest, en conservant la
branche mineure actuelle ; les changements majeurs/mineurs de cette image sont
exclus pour ne pas changer uniquement le Python de test sans celui de l’application.

Les PR ciblent `main` : Dependabot ne découvre pas le sommet d’une pile native.
`target-branch` permet une cible fixe pour les mises à jour de versions, mais
ne suit pas une pile changeante et les correctifs de sécurité ciblent la branche
par défaut. Un suivi dynamique demanderait un contrôleur supplémentaire, non
implémenté ici. Ne pas simplement changer la base d’une PR générée depuis main
sans la rebaser et la retester.

Black est épinglé uniquement dans `requirements/quality.txt`. `make install-quality`
installe cette version et `make format-check` utilise cet environnement isolé.
Ne pas dupliquer la version exacte dans `pyproject.toml` : Dependabot doit pouvoir
mettre à jour le fichier de dépendances sans provoquer un refus de version avant
l’analyse du formatage. Une mise à jour peut néanmoins révéler un changement de
formatage à examiner dans sa PR.

Dependabot maintient les paquets Python, pas le moteur Python lui-même. Une
montée de Python doit actualiser ensemble `.python-version`, les workflows,
les images de test et les instructions locales, puis exécuter les tests.
Le correctif réellement fourni par l’hébergeur doit être vérifié séparément.

## Secrets et historique Git

Activer dans GitHub les alertes de secrets et la protection au push. Ces réglages
ne sont pas contenus dans cette PR. Ils complètent le contrôle local, sans
garantir l’absence de données personnelles, de secrets non reconnus ou de fichiers
sensibles. Les exemples utilisent des données fictives ; `.env`, dumps et fichiers
utilisateurs restent hors Git, y compris dans les artefacts et logs de CI.

`make security-scan` lance Gitleaks sur toutes les références présentes dans le
clone local, avec valeurs masquées. Utiliser un clone complet et synchronisé ;
un clone superficiel ne suffit pas pour un audit historique. Installer Gitleaks
depuis sa distribution officielle et vérifier la somme de contrôle avant usage.
La variable `GITLEAKS` permet de choisir son exécutable. Les résultats sont des
candidats à examiner : une détection peut être une fixture. Ne jamais publier
les valeurs détectées ; ne pas créer d’exception large pour faire passer un scan.
Le code de sortie non nul signale des résultats à examiner, pas nécessairement
des secrets réels. Ce contrôle historique n’est pas ajouté comme job bloquant
de CI ; la protection au push GitHub traite séparément les nouveaux envois.

Un secret réel exposé doit être révoqué ou remplacé, même s’il a depuis disparu
du fichier courant. Un historique Git réécrit ne remplace pas cette révocation.

CodeQL n’est pas activé par ce changement : son périmètre et ses contrôles doivent
être présentés puis validés séparément. Les scans ne remplacent pas les tests
d’accès aux objets, la vérification de configuration ni l’audit réseau de la base.
