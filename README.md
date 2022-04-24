# FreEM LPM

[![DOI](https://zenodo.org/badge/448958805.svg)](https://zenodo.org/badge/latestdoi/448958805)


```diff
- WARNING: This repository is the new repository of [LEM17](https://github.com/e-ditiones/LEM17), which is not maintained anymore
```

FreEM LPM (Lemmas, POS, Morphology). Linguistically annotated corpora of modern French (16-18th c.)

For more information about FreEM corpora, cf. our [website](https://freem-corpora.github.io).


![100% center](images/Punishment_sisyph.jpg)


«Sisyphe portant _CornMol_» (Titian, Prado Museum, Madrid, Spain, Source: [Wikipedia](https://commons.wikimedia.org/wiki/File:Punishment_sisyph.jpg)).

## Data

We provide:
1. [Several authority lists](https://github.com/freem-corpora/FreEMlpm/tree/master/Authority_list), two deriving from [LGeRM](https://www.ortolang.fr/market/lexicons/lgerm).
  * One list contains only propre nouns (`proper`) with the latest added at the end
  * One list contains all the other lemmas (`authority`) with the latest added at the end
  * One list contains all the foreign words (`foreign`) with the latest added at the end
  * Each file has a `_processed` version with all the entries in the alphabetical order, after controlling that there is not twice the same entry
  * On top of these three files, `numbers` contains latin and arabic numbers and `alphabet` contains single latin letters.
2. [Training data](https://github.com/freem-corpora/FreEMlpm/tree/master/Data):
  * _CornMol_ is a gold corpus to be published
  * _FranText_ is a corpus taken from the open data of [FranText](https://www.frantext.fr) and aligned on our lemmatisation standards.
  * _presto_gold_ is a gold corpus used by the [_Presto_ project](http://presto.ens-lyon.fr) tro train their TreeTagger model, converted to CATTEX and lightly corrected to match our authority lists.
  * _presto_max_ have all the modern (16th-18th c.) texts of the _Presto_ project, with lemmas heavily corrected. Each round of annotation/correction is numbered (`v2`, `v3`…)
3. [Out-of-domain testing data](https://github.com/freem-corpora/FreEMlpm/tree/master/Data_outOfDomain) for 16th, 17th, 18th, 19th and 20th c. French
  * Data are separated: theatrical and non theatrical [for historical reasons](https://hal.archives-ouvertes.fr/halshs-02591388).
  * The same data exist in two versions: normalised and original (19th and 20th remains the same, only 16th, 17th and 18th change).
4. The [Models](https://github.com/freem-corpora/FreEMlpm/tree/master/Models) folder contains all the models produced with our data.

```
|-Authority_list
  |-authority_processed
  |-authority
  |-propres_processed
  |-propres
  |-foreign
|-Data
  |-CornMol_gold
  |-FranText
  |-presto_max
  |-presto_gold
|-Data_outOfDomain
  |-Data_outOfDomain_normalised
    |-theatre_normalised
    |-varia_normalised
  |-Data_outOfDomain_original
    |-theatre_original
    |-varia_original
|-Models
  |-train_1
  |-train_2
    |-Models
      |-lemma.tar
      |-pos.tar
```

## Use the lemmatiser
To use the model,
1. Create a (`virtualenv env`) and activate it (`source env/bin/activate`)
2. Install _Pie-extended_: `pip install pie-extended`
3. Download the _freem_ model: `pie-extended download `
4. Use the `freem` model: `pie-extended tag freem your_file.txt`

Do note that _pie-extended_ includes a tokeniser dedicated to (early-)modern French.

## Warnings

The morphology is provided but has _not_ been carefully proofread.

## Licences
<a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/"><img alt="Licence Creative Commons" style="border-width:0" src="https://i.creativecommons.org/l/by/4.0/88x31.png" /></a><br />Our work is licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-sa/4.0/">Creative Commons Attribution 4.0 International Licence</a>.

<a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/"><img alt="Licence Creative Commons" style="border-width:0" src="https://i.creativecommons.org/l/by-nc-sa/4.0/88x31.png" /></a><br />_Presto_ and _LGeRM_ data are licensed under a <a rel="license" href="http://creativecommons.org/licenses/by-nc-sa/4.0/">Creative Commons Attribution 4.0 International Licence</a>.

## Contribute
If you want to contribute, you can do so by cloning the repository and sending us a pull request, or by sending an email at simon.gabay[at]unige.ch.

## Cite this repository

```bibtex
@software{gabay_simon_2022_6481300,
  author       = {Gabay, Simon and
                  Clérice, Thibault and
                  Gille Levenson, Matthias and
                  Camps, Jean-Baptiste and
                  Tanguy, Jean-Baptiste},
  title        = {{FreEM-corpora/FreEMlpm: FreEM LPM (Lemma, POS-
                   tags, Morphology) corpus}},
  month        = apr,
  year         = 2022,
  note         = {If you use this software, please cite it as below.},
  publisher    = {Zenodo},
  version      = {4.0.1},
  doi          = {10.5281/zenodo.6481300},
  url          = {https://doi.org/10.5281/zenodo.6481300}
}
```

```bibtex
@article{jdmdh:7161,
  TITLE = {{Corpus and Models for Lemmatisation and POS-tagging of Classical French
  Theatre}},
  AUTHOR = {Jean-Baptiste Camps and Simon Gabay and Paul Fièvre and Thibault Clérice and Florian Cafiero},
  URL = {https://jdmdh.episciences.org/7161},
  DOI = {10.46298/jdmdh.6485},
  JOURNAL = {{Journal of Data Mining \& Digital Humanities}},
  VOLUME = {{2021}},
  YEAR = {2021},
  MONTH = Feb,
  KEYWORDS = {Computer Science - Computation and Language},
}
```
```bibtex
@inproceedings{gabay:hal-03018381,
  TITLE = {{Standardizing linguistic data: method and tools for annotating (pre-orthographic) French}},
  AUTHOR = {Gabay, Simon and Cl{\'e}rice, Thibault and Camps, Jean-Baptiste and Tanguy, Jean-Baptiste and Gille-Levenson, Matthias},
  URL = {https://hal.archives-ouvertes.fr/hal-03018381},
  BOOKTITLE = {{Proceedings of the 2nd International Digital Tools \& Uses Congress (DTUC '20)}},
  ADDRESS = {Hammamet, Tunisia},
  YEAR = {2020},
  MONTH = Oct,
  DOI = {10.1145/3423603.3423996},
  KEYWORDS = {linguistic annotation ; pre-orthographic language ; lemmatisation ; POS-tagging ; Lemmatisation ; Etiquetage morpho-syntaxique ; POStagging ; Lemmatisation},
  PDF = {https://hal.archives-ouvertes.fr/hal-03018381/file/Lemmatisation.pdf},
  HAL_ID = {hal-03018381},
  HAL_VERSION = {v1},
}
```

Please keep me posted if you use this data!

## Contact
simon.gabay[at]unige.ch
