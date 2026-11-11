# Local recognition model attribution

The unmodified `PP-OCRv6_rec_medium.onnx` weights are derived from PaddleOCR,
copyright Baidu and/or the applicable PaddleOCR rights holders. The ONNX model
conversion and distribution are provided by RapidAI/RapidOCR. The weights and
conversion metadata are distributed under Apache License 2.0. The full license
is included in `licenses/PaddleOCR-Apache-2.0.txt` next to this notice.

Pinned distribution: RapidAI/RapidOCR v3.10.0, ONNX/PP-OCRv6/recognition.
SHA-256: `eef444829dbbe18d7fea59a3f6eb75647518d2b3a9568d27c92e42940204894b`.
The application checks the exact hash before loading the model.

Upstream project: https://github.com/PaddlePaddle/PaddleOCR
Distribution: https://www.modelscope.cn/models/RapidAI/RapidOCR
Licensing and attribution: https://rapidai.github.io/RapidOCRDocs/main/en/model_licenses/

The application authors do not claim ownership of these pretrained weights.
The application's image preprocessing and recognition adapter are separate
code. No real employee image, handwriting crop, or payroll record is embedded
in these public weights or the source repository.

## Clock-specific second reader

`clock_reader_v1.onnx` was trained on fictional clock strings composed from
public EMNIST Balanced glyphs, with synthetic punctuation and image
distortions. The public input hashes are recorded in
`experiments/character_training_evaluation.json`. The trainer is
`experiments/train_clock_reader.py`. The original EMNIST authors are
Gregory Cohen, Saeed Afshar, Jonathan Tapson and André van Schaik.
[NIST EMNIST Dataset](https://www.nist.gov/itl/products-and-services/emnist-dataset)

Model SHA-256
`a6c19d350b488824b31366f3caf71a4994c7223cac20dde18d3d7c0c4bacb60f`.
The application verifies this hash before inference. Payroll forms and their
labels were used for evaluation and selecting the recognition policy.
