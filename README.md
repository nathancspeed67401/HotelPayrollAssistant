# Current candidate — v0.5 engineering build

See [DEVELOPMENT_PROGRESS.md](DEVELOPMENT_PROGRESS.md) for current source, tests, real-photo comparison and open release gates. All numeric OCR results below are historical v0.4 development evidence. No manager release is approved.

# Hotel Payroll Assistant — v0.4 handwriting engineering build

Imports the hotel's handwritten two-week timesheet photos or PDFs, suggests
clock punches locally, shows the original beside editable times, calculates
hours, and exports reviewed Excel payroll for KC.

The new reader aligns the printed grid and uses a pinned PP-OCRv6 whole-entry
model plus the existing digit model. It leaves uncertain or conflicting
readings empty and shows the raw reading for correction. It does not infer
missing AM/PM. All 14 rows still require visual review and sheet approval.

## Measured recognition, October 30, 2026

| Dataset | Correct populated times | Incorrect populated times | Remaining review |
| --- | ---: | ---: | --- |
| Original handwritten development sheet | 11 / 16 unambiguous | 0 | 5 unread, plus 2 without AM/PM |
| Genuine-digit composite forms | 36 / 66 | 0 | 30 unread |
| Printed-font forms | 128 / 128 unambiguous | 0 | 1 without AM/PM |

No false populated times were observed in the 739 blank or struck-out cells
across these checks. These sets were used during development; the one actual
sheet and synthetic forms do not establish accuracy on other writers. This is
an engineering build for supervised testing, not a finished automatic payroll
reader. Details and reproducible commands: [HANDWRITING_BENCHMARK_REPORT.md](HANDWRITING_BENCHMARK_REPORT.md).

## Run from source

Use Python 3.12+ and a locally installed Tesseract OCR 5 executable.

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
python scripts/fetch_ocr_model.py
python main.py --self-test
python main.py
```

The setup command downloads and SHA-256 verifies public recognition weights.
The running reader uses only the local model and disables ONNX telemetry. It
never uploads a sheet or downloads a model while importing payroll data.
Missing or damaged weights leave unread punches for manual review.

## Review and export

1. Add photos or PDFs. The app archives a local copy for later review.
2. Enter the employee and the first Saturday of the pay period.
3. Compare each of the 14 rows with the image, correct punches, and select
   **Checked: Save & Next**, including blank days.
4. Approve the sheet and export Excel. Incomplete punches, invalid times,
   duplicate employees, missing review, or missing source images block export.

Use `12A` for midnight, `12P` for noon, `9:15P` for a clock time, or explicit
24-hour notation such as `21:15`. Saturday–Friday overtime is preliminary until
reconciled with the hotel's official workweek.

## Verify and build

```bash
python -m pytest -q
python experiments/evaluate_pipeline.py --manifest test_samples/real_digit_benchmark/ground_truth.json --output composite-evaluation.json
python experiments/evaluate_pipeline.py --manifest test_samples/ground_truth.json --output font-evaluation.json
```

The evaluation guard requires Linux/libseccomp and blocks network syscalls in
that process. The Windows CircleCI workflow downloads the pinned public model,
runs tests, bundles Tesseract and ONNX Runtime, builds an Inno Setup installer,
silently installs it, and runs dependency/export and GUI smoke checks. See
[BUILD_STATUS.md](BUILD_STATUS.md) for the verified build state.

Real employee scans and predictions are deliberately excluded from this repo.
Keep evaluation reports containing employee punches outside the source tree.
Historical v0.3 results remain in `TEST_REPORT.md` and the earlier fixture OCR
JSON files. Model attribution and its license are packaged in `app/assets`.
