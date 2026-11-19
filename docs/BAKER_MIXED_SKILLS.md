# Fiche boulanger commune

Le parcours courant est décrit dans [le catalogue commun](COMMON_OCCUPATION_SKILLS.md).
La fiche boulanger conserve une liste relue de treize propositions techniques et
sept savoir-être, sans présélection, avec les plafonds communs de cinq et trois.

`eures_beta/skills/data/baker_mixed.json` conserve les références ESCO et ROME,
les libellés sources et les aides de lecture FR/EN/DE. Les recoupements éditoriaux
ne constituent pas des équivalences officielles entre compétences.
Le regroupement métier exige la correspondance officielle exacte D1102 / ESCO
7512.1 (OGR 11573) ; les sources restent internes et vérifiables.

Le libellé français ESCO du pétrissage est ambigu dans l’archive épinglée.
L’aide de lecture s’appuie sur la description et le libellé anglais, sans changer
l’identifiant ni les octets des sources officielles.

Vérification : `make test TESTS=tests.skills.test_baker_mixed`.
