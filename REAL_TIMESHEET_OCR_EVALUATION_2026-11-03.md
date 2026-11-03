# Real Timesheet OCR Evaluation — 3 November 2026

**Release gate: NOT manager-ready for automatic payroll entry.**

## What was inspected
- 19 real photographed two-week timesheets supplied privately by the user (original and cleaned versions).
- The photographs depict the *Comfort Suites Salina South* sheet, which has **one Time In/Time Out pair per day**, plus Date, Rooms, Time Allotted, and Total Hours columns. The earlier prototype mistakenly uses coordinates from a different, **two-pair-per-day** sheet.
- No identifiable employee photograph, employee name, signature, or payroll details were copied into this repository.

## Results of the layout development exercise
- **19/19 cleaned images were classified as the new single-pair form** in a local form-detection pass. This is a test of *layout detection*, **not handwriting accuracy**.
- The local implementation detects paper against the tabletop, normalizes orientation, and aligns day rows to horizontal printed lines before cropping the two relevant punch columns.
- A local-contrast ink check distinguished 16 visibly written punch cells from 12 blank punch cells on the first sample. This is a **one-image spot check only** and does not establish sensitivity/specificity across employees or other handwriting.
- Handwriting transcription is **still poor**: a manual review of that first real image identified 16 filled punch cells, while Tesseract did not produce an exact trustworthy clock-time transcription of them in the local prototype. These samples are much more difficult than the old synthetic font-based or isolated-digit tests.
- A partial batch OCR attempt processed six images before the local execution limit; it is **not** a complete 19-image OCR accuracy benchmark. No overall handwriting accuracy is claimed.

## Implemented changes (experimental)
- Dispatch by actual paper layout instead of trying the old 4-punch grid on every page.
- Preserve the legacy 4-punch parser for the other timesheet style.
- Align printed horizontal rules and crop 14 real day rows from the 2 punch columns.
- Use contrast-relative ink detection to flag faint pencil and pen strokes.
- Keep unreadable or ambiguous OCR in provisional suggestions. Never invent AM/PM for entries such as `6:45`; require manager entry/confirmation.
- Preserve image-aligned review highlights and mandatory 14-day review/approval gating.
- Add synthetic safety tests without private workforce data.

## Needed before a manager release
1. Transcribe/label every filled and blank punch on the 19 real sheets, including which are truly 12-hour or 24-hour times, to create verified ground truth. Separate some sheets for holdout evaluation.
2. Benchmark modern handwriting OCR (e.g. a local line/word model such as TrOCR) on the isolated punch crops. Use trained hand-digit classifiers only as supplementary candidates.
3. Report exact whole-time correctness, false valid readings, missed writing, false positives in blank cells, and per-field confidence; make unconfirmed results *review only*.
4. Run all automated tests and a fresh Windows installer build, install and smoke-test on Windows, then repeat against the untouched real-photo holdout.
5. Confirm the operational meaning of 12-hour times with **no AM/PM** printed on this sheet. It is not safe to infer which half of the day an ambiguous time refers to.

**Bottom line:** The form positioning was corrected for the real sheets, but handwriting recognition still fails the production-quality bar. Do not process wages without checking the paper.
