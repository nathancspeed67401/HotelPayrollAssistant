# Hotel Payroll Assistant — Handwriting Research / v0.3
**Date:** October 28, 2026  
**Status:** Engineering test build, NOT approved for unattended or live payroll.

## What was actually used

The real human-written numerals come from the open **UCI Optical Recognition of Handwritten Digits** collection as distributed through the `scikit-learn` `load_digits()` dataset (1,797 samples). We used indices **0–1099** to train a small SVC digit recognizer and disjoint indices **1100–1796** to generate the test sheets. There was **no download from the UCI website in this environment**; the same public dataset was already bundled with the installed scikit-learn package. Its origin and documentation were independently verified online.

Six fictional, 14-day, two-punch-pair timesheets were built to match the hotel's printed form's page and table geometry. The samples include daylight, overnight, split-shift, late-night, faded, slightly rotated, and JPEG-compressed forms. **Digits are genuine, but whole times, AM/PM letters, names, punctuation, and layout were assembled synthetically**. This is not a true dataset of workers completing timesheets, nor does it verify general handwriting recognition.

## Measured OCR accuracy (entire times, exact match)

| Test | Previous OCR | v0.3 hybrid OCR |
|:--|--:|--:|
| Genuine-digit composite test sheets | **13/66 = 19.70%** | **34/66 = 51.52%** |
| Missed handwritten values | 37 | 22 |
| Incorrect nonblank time values | 16 | 10 |
| False valid time values in blank cells | 0/270 | 0/270 |
| Earlier handwriting-like font set (separate 10 forms) | **103/129 = 79.84%** | **103/129 = 79.84%** |
| Original scanned employee timesheet | Unreliable | **0 usable punches recovered** |

All v0.3 numbers above were obtained with the updated application `scan_page()` and benchmark ground truth, not model predictions alone. The trained digit model uses a **0.90 minimum confidence per individual component** to abstain on uncertain handwriting; other cells still fall back to Tesseract OCR. Model confidence is not a calibrated probability of an entire time being correct. All times remain provisional until the manager visually verifies every row.

A separate model-only experiment accepted **25 of 66** composite time entries at its conservative 0.90 cutoff, all 25 matching the known answers *in this six-form test set*. This is not evidence of 100% real-world accuracy and does not replace the 34/66 end-to-end figure.

## Tests run

- `python -m pytest -q` → **31 passed**.
- `python main.py --self-test` → **passed on Linux** (model load, Tesseract availability, payroll arithmetic and Excel export).
- `python tests/evaluate_real_digits.py` → **34/66 correct** after v0.3 upgrade.
- `python tests/evaluate_ocr.py` → **103/129 correct** (unchanged old baseline).
- The real example `/mnt/data/_timesheet_ref.png` was reprocessed on this machine: **no valid punches populated**.
- **No Windows installer has been built or installed/tested** in this session. Workflows are configured to package the trained model and all necessary dependencies, but they are unexecuted here.

## Limitations and payroll safety

1. The public corpus contains individual digits from a small handwritten-digit benchmark, not complete clock times or names. AM/PM letters are typeset in the benchmark and during model training.
2. Reading the actual employee timesheet is still unsuccessful. Thin, connected, cursive handwritten strokes and cell edges remain difficult.
3. Neither the lower missed-entry count nor the confidence cutoff makes the scanner safe for unattended payroll. The UI's mandatory row-by-row review and approval remain required.
4. The model runs locally on the laptop and requires no OCR cloud account; its larger dependency set may increase eventual Windows installer size.
5. Do **not** enter real payroll solely from machine-generated values without human verification against signed paper records.

## Suggested next engineering work

- Evaluate a modern line-oriented handwriting model such as Microsoft TrOCR (small handwritten), **on cropped boxes** and on the real form, as a separate alternative; do not ship it until a model and its dependencies can be built and tested offline.
- Capture a consented set of 30–50 anonymized real handwritten sheets from various writers. Score each filled punch and blank independently, with separate development and untouched evaluation sets.
- Benchmark color vs pencil, low light, angle, smudges, crossed-out entries, blank days, AM/PM and `12A` notation.
- Run an actual Windows CI installer build and end-to-end smoke test.

## Public-source links

- UCI corpus: https://archive.ics.uci.edu/dataset/80/optical%2Brecognition%2Bof%2Bhandwritten%2Bdigits
- scikit-learn copy: https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_digits.html
- Optional next model research: https://huggingface.co/microsoft/trocr-small-handwritten
