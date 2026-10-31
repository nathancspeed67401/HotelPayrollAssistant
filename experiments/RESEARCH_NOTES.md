# Follow-up recognition experiments — October 30, 2026

The packaged v0.4 reader remains the implementation verified in Windows job 8
at source `7a242619cb55b5d30f70be42a7f87b1806df7774`. None of the experiments
below changes the packaged reader or its 11/16 development-scan result.

## Larger line model

Microsoft `trocr-base-handwritten`, revision
`eaacaf452b06415df8f10bb6fad3a4c11e609406`, was downloaded separately and run
locally under the outbound-network deny filter. On the original scan, raw
registered crops produced one correct and one incorrect valid time; tight
blue-ink crops produced nine correct and one incorrect valid time. Both views
left blank and suffix-missing cells without a valid time. These are recognizer
outputs, not the app's acceptance policy, and do not improve the shipped reader.
The much larger model is excluded from the application and dependencies.

Historical TrOCR experiment score fields could include zero-probability padding
because the composite config lacked decoder token IDs. The experiment now uses
the generation config/decoder IDs and excludes padding, with explicit regression
checks. The counts above use strict parsed text only, not those old score fields.

## Row-boundary padding and isolated suffixes

Expanding registered rows above and below by 10%, 18%, and 25% of row height
produced 10, 11, and 11 correct unambiguous punches respectively, with no wrong
or false-filled blank times observed. The existing reader already recovered 11.
The expanded crops are excluded. Isolating the final ink component helped one
A reading but did not resolve the other ambiguous A/4 shapes consistently.
No rule that blindly converts a final 4 to A was introduced.

## Public handwritten-character CNN

A small convolutional classifier was trained only on the public EMNIST Balanced
character corpus. Source and corpus authorship are documented at:
https://www.nist.gov/itl/products-and-services/emnist-dataset

The NIST download returned HTTP 403. The dataset authors' published Western
Sydney University distribution was obtained at:
https://rds.westernsydney.edu.au/Institutes/MARCS/BENS/EMNIST/emnist-gzip.zip

That ZIP has different packaging from the ZIP identified by torchvision's
NIST archive MD5. Its SHA-256 is
`909a2a39c5e86bdd7662425e9b9c4a49bb582bf8d0edad427f3c3a9d0c6f7259`.
The four individual balanced-subset gzip payload hashes matched independently
published copies; all actual payload hashes are recorded in the training report.
No mismatched archive was described as passing the NIST archive hash check.

Training used a fixed seed and six epochs: 101,520 training characters and
11,280 validation characters from the official training split. The separate
18,800-character official test split was evaluated only after training and
scored 84.89% character accuracy. This is not whole-time accuracy. The actual
scan was never a training input. The classifier's suffix predictions on its
unread punches were uncertain, so its weights are excluded from the application.
The reproducible trainer is `train_character_cnn.py`; public training metadata
is `character_training_evaluation.json`. PyTorch is an experiment dependency,
not a payroll application dependency.

All employee images, crops, ground truth and predictions remain outside this
repository. Recognition still needs broader, independently transcribed natural
handwriting to establish performance on other writers. The current reader
keeps every row subject to human review and sheet approval.
