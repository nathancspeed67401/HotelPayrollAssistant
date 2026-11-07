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
- The final CI run must provide fresh full-tree results; prior passing reports
  do not substitute for the final source check.

## Windows installer

Inno Setup version is now 0.5.0 (engineering candidate). The existing CircleCI
Windows job installs dependencies, verifies/bundles the offline model and
Tesseract, runs all tests, packages the EXE, builds and silently installs setup.
The installed GUI self-test now exercises PDF loading, actual registered OCR,
manual correction, every-row sign-off, approval, Excel export, restart recovery,
duplicate prevention and export blocking after edits. CI also silently uninstalls
and checks that the executable is removed. Verification text, source SHA,
dependencies, installer SHA-256 and setup are configured as artifacts.

Historical PR 3 source had a successful GitHub-reported CircleCI job 23; this is
not validation of the new source. Fresh candidate build status and artifact
retrieval are pending. No new installer is declared production-ready.

## Remaining release gates

1. Reliable registration and visual crop verification for every supplied layout
   and photo, plus rotated/perspective/compressed/low-light variants.
2. Complete, independently checked ground truth for all 19 sheets, preserving
   unreadable/corrected entries, and a frozen held-out comparison. The three-sheet
   development result is far below 98% and is not an independent benchmark.
3. Broader written-vs-blank sensitivity and correction detection; model confidence
   remains uncalibrated. Further recognition tuning must retain abstention rules.
4. Fresh Windows build/install/workflow/uninstall evidence for this exact source,
   artifact retrieval and checksum verification, and a real manager usability
   check. Windows CI alone does not establish Windows 10/11 field compatibility.
5. Confirm the employer-defined overtime workweek and ambiguous real AM/PM
   conventions before representing overtime estimates as final wage calculations.

No paid service, cloud OCR, employee upload, API-key screen or subscription was
introduced. The importer reads locally and does not download models at runtime.
