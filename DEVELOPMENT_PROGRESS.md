# Development and release evidence — November 6, 2026

**Release decision: engineering candidate only. Not approved for live payroll.**

## Source recovery and completed engineering

- Inspected the repository, all three PRs, available issue search, source, tests,
  dependencies and CircleCI configuration. GitHub Actions had no runs.
- Integrated both parent histories: PR 2's pinned offline PP-OCRv6 engine and
  aligned legacy reader, plus PR 3's actual single-pair form support, orientation
  correction, archival and review UI. Integration commit:
  `f157301741b1dd8fba522e4b6ca0e53bafbca98f`.
- Recovered all 19 original photos and both cleaned archives. The two cleaned
  archives contain alternate copies, not additional employees. No private
  photo, employee name, signature, ground truth or prediction is in Git.
- Found that the old global row transform could crop headers, totals, adjacent
  rows and clipped leading digits. The new registration fits printed rules and
  headers, uses the printed Saturday anchor, accounts for tall header cells,
  rectifies individual cell quadrilaterals, and records image-space review boxes.
  Failed registration produces no fixed-position time guesses.
- Added grayscale/local-contrast recognition views for black ink and faint
  pencil; blue-only masks are unsuitable for these photos. PP-OCR suggestions
  preserve raw readings, candidate sources and uncalibrated confidence metadata.
  Missing AM/PM, omitted minutes and plausible disagreements remain unresolved.
- Bound each row's visual review and sheet approval to the actual data. Editing
  punches, identity, period, source or recognition evidence invalidates approval.
  Export checks current review evidence and source image integrity itself.
- Empty cells with unresolved writing require explicit blank/crossed-out
  confirmation. OCR never counts as human verification. A leading zero on a
  handwritten time does not establish a 24-hour convention.
- Added crash-recoverable per-page import journals, fsynced atomic session writes,
  previous-session backups, preservation of earlier pay periods, and an exclusive
  application lock. Imports persist incrementally and do not interrupt review.
- Added atomic Excel replacement, formula/URL injection protection, cached Excel
  totals, normalized employee duplicate checks and duplicate-image rejection.
  Export is blocked while a selected import is still running.
- Added a split-shift span check. Printed-day assignment and Saturday–Friday
  reporting remain unchanged. Overtime remains explicitly an estimate until the
  employer's fixed workweek and actual timing convention are confirmed.

## Fresh OCR evidence and its limits

Blind initial visual labels cover 84 cells on three development sheets:
35 readable written punches, 44 blank/struck-out cells and 5 ambiguous/corrected
cells excluded from exact transcription scoring. **No independent reviewer has
verified these labels.** This is not the requested complete 19-sheet benchmark.

| Engine | Exact raw clock transcriptions / 35 | Wrong raw clocks | Raw clocks on 44 blank/struck-out cells |
| --- | ---: | ---: | ---: |
| PP-OCRv6 medium, strongest of four registered grayscale views | 26 | 2 | 0 |
| Existing Tesseract photo-cell reader | 1 | 4 | 0 |
| Local Microsoft TrOCR base handwritten, raw registered crops | 0 | 0 | 1 |

These raw outputs are not payroll approvals. The conservative PP-OCR decision
policy produced **7 populated time suggestions**, all matching these provisional
labels, and no populated blank or ambiguous cells in this development comparison.
The other written cells remain for manual entry or clarification. After removing only residual printed cell perimeters, the ink detector missed zero of the 35 readable written punches and flagged all six struck-out cells for review while leaving the other 38 blank cells blank in this small development check. These results
do not establish a production error rate or calibrated confidence.

TrOCR was downloaded at revision `eaacaf452b06415df8f10bb6fad3a4c11e609406`
and executed locally with network syscalls blocked. It is excluded from the
installer because it did not improve this comparison. The packaged model remains
the existing SHA-256-pinned PP-OCRv6 medium ONNX model. Research dependencies are
not runtime dependencies. Timing in these concurrent experiments is not a fair
ordinary-laptop performance comparison.

At this checkpoint, registration succeeded on **10/14 development originals**;
four conservatively fail and need further work. Registration success is not a
complete visual audit of every crop or handwriting accuracy. Never advertise it
as clock-punch accuracy.

Four sheets are reserved for final recognition evaluation. An initially reserved
first sheet was excluded because historical reports show it was used in prior
OCR development. Originals, cleaned copies and augmentations stay in the same
split. No writer-independent claim is made. The evaluation code rejects duplicate
cells, counts missing predictions as misses, separates ambiguous/blank errors,
tracks confidence bins, and prevents incomplete, unreviewed or development-only
results from satisfying the 98% target. The independent 98% target is **unmet**.

## Frozen reserved-sheet result

The recognizer and registration code were frozen in `f25938ab3520b501c28f9b3b3e2ce4bae799a56a`
before viewing this split's punch labels. The actual importer ran offline on all
four reserved originals. Two registered and two abstained at registration; the
failed sheets count against accuracy rather than being discarded.

| Measure | Observed result |
| --- | ---: |
| Visually transcribed cells | 112 |
| Readable written values | 65 |
| Blank or struck-out cells | 42 |
| Ambiguous/corrected cells | 5 |
| Exact raw clock transcriptions | 18 / 65 (27.7%) |
| No raw reading | 28 |
| Wrong formatted raw reading / other invalid raw text | 1 / 18 |
| Correct populated time suggestions | 4 / 65 (6.2%) |
| Wrong populated times / filled blanks | 0 / 0 observed |

All labels are provisional, with no independent reviewer. Some readable clock
numbers lack AM/PM and cannot authorize a payroll time. Among 30 predictions
with nominal confidence at least 0.9, only 17 matched the initial labels. This
is direct evidence against treating the model's score as verified accuracy.
Seven sheets now have 196 initial labels. All 19 original identities are pinned
by SHA-256, and the other 12 still require transcription. The private checkpoint
preserves these labels and measured counts outside the repository.

`experiments/scan_real_forms.py` now reproduces private pipeline runs, verifies
original file hashes and supports rotation, dim lighting, JPEG compression and
perspective diagnostics. Score each variant independently with
`experiments/evaluate_real_forms.py`. No payroll images or per-cell results
belong in Git or CI artifacts.

On one labeled development sheet, the original and each of the four generated
variants (180° rotation, dimmed, JPEG quality 45, and a small perspective warp)
registered and transcribed **5 of 8** readable punches exactly. Each produced
five correct populated suggestions and no wrong populated or filled blank cells.
This single-sheet diagnostic is not an estimate of robustness across writers.

## Automated verification

- PR 2 baseline: **63 passed, 3 GUI tests skipped** before integration.
- Integration-focused layout/orientation/calculation checks: **18 passed**.
- Full candidate suite with a real virtual desktop: **105 passed, zero skipped**
  before the final archive-preservation regression. Includes actual widgets, source preservation,
  corrections, approval invalidation and the complete desktop workflow.
- Follow-up OCR/benchmark/approval checks: **38 passed**. Archive/source and approval regression group: **19 passed** after the archive fix. Additional batch export
  and duplicate-image checks: **22 passed** in their selected regression group.
- Actual ONNX/Tesseract/calculation/export self-test passed with network syscalls
  blocked. The synthetic desktop import/review/approve/export/restart workflow
  passed locally. Private employee sheets were not used in CI.
- The committed `f25938a` candidate passed **106/106** local tests, including
  the desktop workflow on a virtual display. Inspection then found the row
  table could crowd the editor out at laptop window heights. The editor now
  reserves room before the scrollable table. Single-pair forms show only two
  inputs, and an inaccessible source clears the previous image from view.
- The revised candidate passed **108/108** local tests, with no skips, on a
  real virtual desktop. A visual check at 1366×768 confirmed that both time
  boxes, the selected row image, and the check-and-advance button are visible.
  The focused archive/export and scoring checks also
  passed **27/27**. Windows verification remains separate.

## Windows installer

Inno Setup version is now 0.5.0 (engineering candidate). The existing CircleCI
Windows job installs dependencies, verifies/bundles the offline model and
Tesseract, runs all tests, packages the EXE, builds and silently installs setup.
The installed GUI self-test now exercises PDF loading, actual registered OCR,
manual correction, every-row sign-off, approval, Excel export, restart recovery,
duplicate prevention and export blocking after edits. CI also silently uninstalls
and checks that the executable is removed. Verification text, source SHA,
dependencies, installer SHA-256 and setup are configured as artifacts.

Historical PR 3 source passed CircleCI job 23. The new candidate's
[Windows job 24](https://circleci.com/gh/nathancspeed67401/HotelPayrollAssistant/24)
reported failure on GitHub. The private job logs and artifact listing were
not accessible here, so its exact failing step is unconfirmed. The follow-up
corrects a concrete Windows compatibility issue: flush the temporary archive
and workbook with writable handles, as required by
[Windows file flushing](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers).
[Windows job 25](https://circleci.com/gh/nathancspeed67401/HotelPayrollAssistant/25)
reported **success** on exact source `21e666954f43eef2b340235f6d1bf384d0529910`.
The configured job includes the full test suite, setup compilation, silent
installation, real bundled OCR/export checks, installed GUI import/review/
approval/export/restart checks, and silent uninstall. The pass was verified
through GitHub's exact-commit status. Job 24's specific failure remains unknown.

The configured setup artifact is `Windows-Setup/HotelPayrollAssistant_Setup.exe`.
The two private artifact-list requests returned HTTP 404 from this session,
so the binary and its checksum were not retrieved or independently verified.
For supervised testing, use the job's **Artifacts → Windows-Setup** section.
Run the setup on a test Windows account, keep the desktop shortcut selected,
then open Hotel Payroll Assistant and use fictional forms. The CI executor is
Windows Server 2022; this is not a field test on Lynnette's Windows 10/11 laptop.
The installer remains an engineering candidate.

## Remaining release gates

1. Reliable registration and visual crop verification for every supplied layout
   and photo, plus rotated/perspective/compressed/low-light variants.
2. Complete, independently checked ground truth for all 19 sheets, preserving
   unreadable/corrected entries, and a frozen held-out comparison. The three-sheet
   development result is far below 98% and is not an independent benchmark.
3. Broader written-vs-blank sensitivity and correction detection; model confidence
   remains uncalibrated. Further recognition tuning must retain abstention rules.
4. Retrieve and checksum the setup file, test on supported Windows 10/11, and
   complete manager usability acceptance. Job 25 closes the CI build and
   installed-workflow gate only.
5. Confirm the employer-defined overtime workweek and ambiguous real AM/PM
   conventions before representing overtime estimates as final wage calculations.
   The [Department of Labor's workweek guidance](https://www.dol.gov/agencies/whd/fact-sheets/23-flsa-overtime-pay)
   distinguishes the fixed workweek from a biweekly pay period. The paper form
   also mentions a meal-break deduction with a front-desk exception. The app
   currently totals elapsed punch intervals and does not apply automatic break
   deductions or quarter-hour rounding. Confirm the hotel's actual rules and
   which intervals are payable before using the export to pay wages.

No paid service, cloud OCR, employee upload, API-key screen or subscription was
introduced. The importer reads locally and does not download models at runtime.
