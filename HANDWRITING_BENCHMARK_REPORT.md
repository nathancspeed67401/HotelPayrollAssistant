# Handwriting recognition development report — October 30, 2026

## Current implementation

The reader locates neutral printed grid lines, validates all four clock columns
and both seven-row sections, and corrects individual cell perspective. This
fixes the bottom rows' leading clock-out digits being clipped by fixed crops.
If a reliable grid cannot be found, fixed crops are retained with a warning.

A local PP-OCRv6 medium recognition graph reads each visible whole entry through
four image views: original color, isolated blue ink, cleaned blue ink, and a
narrower ink crop. The existing UCI digit model adds conservative suggestions
and flags plausible disagreements. A conflicting plausible time remains empty;
a weak single view cannot fill a punch. Invalid text is not stripped into a
valid time, and a terminal digit 4 is never converted to A. Missing AM/PM stays
unresolved. Model confidence is a heuristic, not a calibrated accuracy claim.

The ONNX weights are pinned to RapidAI/RapidOCR v3.10.0 and verified against
SHA-256 `eef444829dbbe18d7fea59a3f6eb75647518d2b3a9568d27c92e42940204894b`.
The runtime disables ONNX telemetry before opening a session. The application
contains no model downloader; the separate public-weight setup/build command
fetches the model before any employee sheet is processed. All private-sheet
experiments also ran under a Linux process-wide outbound-network deny filter.

## End-to-end results

These numbers use `app.ocr.scan_page()`, not selected recognizer outputs.

| Set | Valid filled truth | Correct | Unread | Incorrect filled | Blank cells | False filled blank | Ambiguous truth | Ambiguous auto-filled |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Original handwritten development scan | 16 | 11 | 5 | 0 | 38 | 0 | 2 | 0 |
| Six genuine-digit composite forms | 66 | 36 | 30 | 0 | 270 | 0 | 0 | 0 |
| Ten printed-font forms | 128 | 128 | 0 | 0 | 431 | 0 | 1 | 0 |

The 129 written cells in the font set contain 128 unambiguous times plus one
entry without AM/PM. The new count reports that ambiguous cell separately;
it is not silently counted as correct recognition.

A/4 confusion remains the main failure in the five unread unambiguous punches.
Two other written punches omit AM/PM and must be resolved from an authoritative
record.
No actual employee name, source image, crop, or per-cell private prediction is
included in this repository.

A fresh run of the old pipeline on the original scan recovered zero correct
unambiguous punches and incorrectly filled one suffix-missing entry. Historical
v0.3 composite results were 34 correct, 22 unread, and 10 incorrect of 66, with
zero false positives in 270 blanks. The earlier printed-font result was 103/129.
Those historical counts are retained as history, not freshly rerun baselines.

## What these tests establish

The six composite forms use held-out UCI `load_digits()` images from indices
1100 onward; clock strings, suffixes, names, punctuation, and layout were
synthetically assembled. The digit recognizer was trained on indices 0–1099.
These are real individual digit shapes, not naturally completed timesheets.
The other ten forms use printed italic fonts. The original scan is only one
real writer and was used for development. None of these sets is an untouched
validation set for the new image views and decision policy. Zero observed wrong
entries here does not establish zero errors on new handwriting.

TrOCR small and RapidOCR v5 English/small/medium were compared offline.
The shipped adapter uses only ONNX Runtime and the medium public model; it does
not require PyTorch, Transformers, RapidOCR's download manager, or cloud OCR.

## Reproduce

Install the pinned requirements and run `python scripts/fetch_ocr_model.py`.
Then run:

```bash
python -m pytest -q
python main.py --self-test
python experiments/evaluate_pipeline.py --manifest test_samples/real_digit_benchmark/ground_truth.json --output composite-evaluation.json
python experiments/evaluate_pipeline.py --manifest test_samples/ground_truth.json --output font-evaluation.json
```

The evaluation commands require Linux/libseccomp and deny outbound networking
before opening inputs. The saved aggregate and mismatch reports for public
fixtures are `test_samples/real_digit_benchmark/aligned_line_evaluation.json`
and `test_samples/aligned_line_evaluation.json`.

Fresh local checks: 63 tests passed, three GUI tests skipped because this Linux
session has no display; the real-model installation/export self-test passed
under the offline process guard. The new Windows installer workflow
passed as CircleCI job 8 on source `7a242619cb55b5d30f70be42a7f87b1806df7774`,
including installed-model and GUI checks. See `BUILD_STATUS.md`.

## Release state

The supervised reader is materially improved. General handwriting reliability
remains incomplete, and all 14 days require visual review and approval before
export. A larger set of independently transcribed natural handwriting from
multiple writers is still needed before claiming broad recognition accuracy.
