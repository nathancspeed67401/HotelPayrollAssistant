# Hotel Payroll Assistant — Synthetic Timesheet Test Report
**Date:** October 28, 2026  
**Build:** 0.1.1 (testing and safety improvements)  
**Overall:** **Payroll calculations pass. Handwriting recognition does NOT pass for unattended use.**

## What I created

Ten fictitious two-week timesheets modeled on the paper form, with 14 daily rows and two pairs of in/out punches per day. They include daytime shifts, midnight/overnight shifts, split shifts, overtime, mixed formats, faded/rotated scans, a blurry phone-style scan, an incomplete punch, an ambiguous time, and an entirely blank timesheet.

Files: `test_samples/01_...png` through `10_...png`, combined printable `Synthetic_Test_Timesheets.pdf`, machine-readable `ground_truth.json`, raw `ocr_results.json`, and summary `ocr_summary.csv`.

**Important:** The names and shifts are fictional. The writing is rendered using handwriting-like italic fonts, **not naturally written pen strokes**. This is a useful software regression test, **not** a reliable prediction of performance on real handwritten timesheets. Images were generated from scratch; no real employee's scanned timesheet is bundled.

## OCR accuracy — actual test results

| Test case | Exact punches / written punches | Incorrect valid readings | Unrecognized punches |
|---|---:|---:|---:|
| 01 Daytime | 19 / 20 | 0 | 1 |
| 02 Overnight | 15 / 16 | 1 | 0 |
| 03 Split shifts | 27 / 32 | 2 | 3 |
| 04 Overtime | 14 / 22 | 0 | 8 |
| 05 Mixed shifts | 9 / 10 | 1 | 0 |
| 06 Varying fonts / slight rotation | 8 / 12 | 1 | 3 |
| 07 Missing clock-out (intentional) | 3 / 3 | 0 | 0 |
| 08 Missing AM/PM (intentional) | 2 / 4 | 0 | 2 |
| 09 Blurred, tilted phone-style photo | 6 / 10 | 1 | 3 |
| 10 Blank | 0 / 0 | 0 | 0 |
| **TOTAL** | **103 / 129 (79.84%)** | **6** | **20** |

Across 431 purposely empty punch cells, the program inserted **0 false valid times** in this synthetic dataset. Note that 79.84% refers to *populated punch cells*, not employees, shifts, rows, or a validated field accuracy on real handwriting. The program extracted **9 of 10 employee names exactly** after adding a spacing cleanup; the remaining name contained an extra character.

Some errors are particularly dangerous: `12P` can be read as `2P` (both valid-looking times), and `12A` can become `127A` or `112A`, which Tesseract's time parser may treat as other valid times. Without review, either changes wages. The real original timesheet is materially harder than the generated sample.

## Original scanned handwritten timesheet — separate privacy-safe spot check

Tested the real sample supplied in the conversation. The current local Tesseract system recognized **0 valid clock punches** automatically, **did not successfully read the employee's name**, and marked **28 possibly written cells for human inspection**. These figures measure behavior of this prototype, not a benchmark of handwriting OCR generally. The source scan is **not included** in the downloadable test dataset or code ZIP.

**Verdict:** The existing Tesseract-based OCR pipeline is not adequate for the advertised scan-and-review experience on that real form. Even the synthetic samples are much too error-prone to rely on without comparing every cell to the photo.

## Non-OCR tests — passed

- **24 automated tests passed**, covering multiple schedule patterns, weekly totals, distinct weekly overtime, overnight and split shifts, blank forms, missing punches, ambiguous AM/PM, duplicate employees, approval gating, session save/reopen, PDF import, and Excel export.
- **Actual Excel file successfully generated** from an approved fictional test batch and inspected as a valid multi-sheet XLSX archive with summary rows and time details.
- **PDF import smoke test passed**: a ten-page PDF opened as ten images; the first PDF page was processed by OCR and found 20 valid-looking clock entries (this alone does not guarantee every entry was correct).
- **Linux GUI startup smoke test passed** using a virtual display. This is **not** a Windows installer test.
- **Generated PDF rendered successfully** across all ten pages.

## Fixes made during this test

1. Faster blank-cell screening avoids unnecessary OCR attempts and helps prevent blank cells turning into spurious times.
2. Basic employee-name spacing restoration (e.g. `AveryWilson` -> `Avery Wilson`).
3. A warning is recorded when writing is detected but a valid clock time cannot be read.
4. Unreadable rows are marked **CHECK OCR** in the review interface. The manager must explicitly confirm review to approve. Saving a reviewed row clears its prior warning; invalid or missing punches still block export.
5. Added reproducible test generator, benchmark script, ten source images, ground truth, OCR result data, and additional regression tests.

## Remaining blockers

1. **Replace or supplement Tesseract with a stronger handwriting recognizer**, benchmarked on at least 10-20 verified *real* examples. OCR must never finalize pay unreviewed.
2. **Image alignment**: the current program uses fixed crop coordinates and can misread angled/poorly cropped photos.
3. **Windows installer**: source and build recipe exist, but no Windows `.exe` was built or tested here. **Do not give the prototype to the manager as a finished installer.**
4. **Employer overtime workweek**: the summary uses Saturday-Friday form weeks to estimate overtime. Validate the official fixed workweek with KC before payroll use.

**Use for:** reviewable software demonstration and developer testing. **Not for:** finalizing actual employee payroll based on unverified OCR readings.
