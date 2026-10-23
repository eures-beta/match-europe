# Modèles locaux Tesseract FR / EN / DE

Source officielle : https://github.com/tesseract-ocr/tessdata_fast
Commit : `87416418657359cb625c412a48b6e1d6d41c29bd`.
Licence Apache 2.0 conservée dans `LICENSE`.

Ces modèles sont livrés avec le code pour éviter tout téléchargement pendant
le traitement des documents. Aucun service OCR distant n’est utilisé.
Tesserocr utilise le même moteur Tesseract que l’outil système ; PDFium rend
les pages scannées si Poppler est indisponible. Les limites de taille et le
processus séparé du lecteur restent actifs.

SHA-256 :

- fra.traineddata : `ced037562e8c80c13122dece28dd477d399af80911a28791a66a63ac1e3445ca`
- eng.traineddata : `7d4322bd2a7749724879683fc3912cb542f19906c83bcc1a52132556427170b2`
- deu.traineddata : `19d219bbb6672c869d20a9636c6816a81eb9a71796cb93ebe0cb1530e2cdb22d`

Volume total des trois modèles : environ 6,8 Mo.
