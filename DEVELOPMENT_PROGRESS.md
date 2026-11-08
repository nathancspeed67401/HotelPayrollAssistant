# Development progress · November 7, 2026

**Engineering candidate based on v0.5.2. The installer is verified for supervised testing with fictional data. Live payroll acceptance is open.**

## OCR and Windows release follow-up

[PR #5](https://github.com/nathancspeed67401/HotelPayrollAssistant/pull/5) is
the engineering candidate. The tested source is
[`cbe6022463429fa6b42bd94613bb77ba0a448b0c`](https://github.com/nathancspeed67401/HotelPayrollAssistant/commit/cbe6022463429fa6b42bd94613bb77ba0a448b0c).
The baseline is `fe4c8486f84a431884a76cb4ef961e43828ff14a`. Main was
`9a46c916334d56e9460a3939a2b7a497caf445d0` when this work started.

- Clock reading accepts alternate punctuation in a fully written clock and
  normalizes full-width characters. A shorthand hour supplies no evidence
  for written minutes. A faint-ink threshold scales with local paper
  brightness and still requires a connected ink pattern.
- New imports of either form keep OCR suggestions in the review controls.
  The manager deliberately enters or accepts a punch, checks every row,
  then approves the sheet. A prior saved session retains its entries and
  review state.
- All 19 original hashes matched. The split is 14 development, four
  reserved regression and one historical development sheet. The 532 labels
  are first-pass annotations. The scorer and split stayed fixed across the
  baseline and candidate. No fresh writer-disjoint acceptance set was available.

| Private dataset | Registered | Exact raw | Correct suggestions / eligible | Manual entries | Unsafe suggestions |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development originals | 14/14 → 14/14 | 110/151 → 112/151 | 27/50 → 28/50 | 124 → 123 | 0 → 0 |
| Development dimmed | 13/14 → 13/14 | 105/151 → 109/151 | 24/50 → 24/50 | 127 → 127 | 0 → 0 |
| Development perspective | 13/14 → 13/14 | 106/151 → 108/151 | 23/50 → 24/50 | 128 → 127 | 0 → 0 |
| Reserved originals | 4/4 → 4/4 | 36/65 → 39/65 | 5/26 → 7/26 | 60 → 58 | 0 → 0 |

| Private dataset | Readable punches missed in failed registrations | Wrong raw clocks | Invalid raw | Readable punches flagged blank | Clean blanks sent to review |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development originals | 0 → 0 | 6 → 6 | 35 → 33 | 0 → 0 | 0 → 0 |
| Development dimmed | 4 → 4 | 7 → 7 | 33 → 31 | 2 → 0 | 0 → 0 |
| Development perspective | 4 → 4 | 7 → 7 | 34 → 32 | 0 → 0 | 0 → 0 |
| Reserved originals | 0 → 0 | 3 → 3 | 26 → 23 | 0 → 0 | 4 → 5 |

The candidate flagged all 30 crossed-out development cells and all 14
crossed-out reserved cells, and offered zero suggestions on them. Wrong
suggestions on readable punches were zero in these runs. The dim run now
sends both faint punches to the reader. Alternate crops and three other
offline model weights produced limited gains or more errors on development.
Thirty-five readable development entries had no minutes and 66 had minutes
without AM/PM. The reserved sheets had 39 entries without AM/PM. The reserved
exact result is 60.0% against the 98% target. Manual-entry counts measure
readable punches without a correct complete suggestion. Each row still needs
visual review.

### Verification

The full candidate suite passed 143 tests on Linux with zero skips
(131 non-GUI and 12 desktop). The model/workbook self-test and desktop
import/review/approve/restart/export self-test also passed. The test
processes ran with outbound network system calls blocked and the desktop
display preconnected over loopback.

```sh
python scripts/fetch_ocr_model.py
python -m pytest -q --ignore=tests/test_ui_safety.py
python -m pytest -q tests/test_ui_safety.py
python main.py --self-test
python main.py --gui-self-test
python experiments/evaluate_pipeline.py --manifest test_samples/ground_truth.json --output "$PRIVATE_DIR/fictional-fixture-evaluation.json"
```

The fictional-fixture evaluator offered 128 of 128 expected complete hints,
with zero autofilled punches, no suggestions on 431 blank cells, and one
ambiguous cell left for entry.

The offline desktop batch imported 22 fictional photos and eight PDFs,
blocked the missing punch and unapproved export, checked 420 rows and
restored all 30 approvals. OpenPyXL independently reconciled the 420 dates
and exact-minute totals. The first printed week totaled 18,196 minutes and
the second 18,474, for 36,670 elapsed minutes with one overtime minute.
The batch includes a Friday overnight crossing into Saturday, a midnight
start, and two-pair split shifts. See [Release status](RELEASE_STATUS.md)
for the same test inputs and expected outputs on Lynnette's PC.

The benchmark commands below also apply to this source and its baseline.
Use the same first-pass manifest and only the development splits to tune.
The four reserved sheets remain a regression check. Before a new acceptance
run, independently verify the labels and freeze the source SHA and the
unchanged scoring rules. Add fresh photos from different writers and use the
acceptance split with `--reference-manifest` to enforce writer separation.

### Windows and release gates

[CircleCI Windows job #31](https://circleci.com/gh/nathancspeed67401/HotelPayrollAssistant/31)
passed for `cbe6022463429fa6b42bd94613bb77ba0a448b0c` using the existing
offline Windows workflow. The earlier [job #30](https://circleci.com/gh/nathancspeed67401/HotelPayrollAssistant/30)
failed for `fe4c8486f84a431884a76cb4ef961e43828ff14a`. Its first failing
step still requires the signed-in log. [Job #29](https://circleci.com/gh/nathancspeed67401/HotelPayrollAssistant/29)
passed for an earlier source commit.

The uploaded setup was independently hashed and matched the SHA-256
supplied for job #31. The copied `source-commit.txt` matched the exact
passing commit. [Build status](BUILD_STATUS.md) records the digest, size
and embedded signature check. The installer is ready for supervised
testing with fictional forms.

Live use requires fresh OCR acceptance, Lynnette's Windows acceptance
and the payroll owner's output and policy approval. The workweek follows the
Saturday–Friday printed rows. Review the 15-minute housekeeping break
requirement manually for days over five hours and calculate from the actual
punches. The workbook uses exact minutes with zero automatic deductions.
The separate meal treatment and payroll rounding or exact-minute policy
still require confirmation.

## Previous OCR iteration

[PR #5](https://github.com/nathancspeed67401/HotelPayrollAssistant/pull/5) starts at
[`9a46c916334d56e9460a3939a2b7a497caf445d0`](https://github.com/nathancspeed67401/HotelPayrollAssistant/commit/9a46c916334d56e9460a3939a2b7a497caf445d0).
The exact frozen OCR source is
[`fbeb143768d359fb543aa0ca366fff35077e6d7b`](https://github.com/nathancspeed67401/HotelPayrollAssistant/commit/fbeb143768d359fb543aa0ca366fff35077e6d7b).

| Commit | Change |
| --- | --- |
| `c2d3f4ea800a98d85754ae1cdd51fff5839d90bf` | Require observed boundaries for all 14 rows, printed weekday anchors in each week and the printed rules enclosing both clock columns across both weeks. Retry weak printed rules and recover tall headers and upright tables when the page heading is unreadable. |
| `12c36129f52b5e1f8f595e7af9f48f82cc0d1dc8` | Count readable cells on failed registrations as misses. Count unsafe hints and blank and crossed-out errors separately. |
| `fbeb143768d359fb543aa0ca366fff35077e6d7b` | Rectify each punch from its original photo pixels. Apply the existing ink gate at the normalized crop scale and pass the native crop to the pinned offline PP-OCRv6 reader. |

The original hashes matched all 19 checkpoint records. The benchmark retained
the 14 development sheets, four frozen reserved sheets and one historical
development sheet. All 532 labels are first-pass annotations. The candidate
and settings were frozen before either new reserved run. The dim and
perspective variants use the same development originals and labels.

### Private benchmark results

Each pair shows the v0.5.2 baseline followed by the frozen candidate. Exact
raw scoring preserves the presence of minutes and AM/PM. A manual entry is a
readable punch without a correct hint. Every row still needs review.

| Dataset | Registered | Exact raw | Correct hints / eligible | Unsafe hints | Manual entries |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development originals | 13/14 → 14/14 | 101/151 → 110/151 | 22/50 → 25/50 | 1 → 0 | 129 → 126 |
| Development dimmed | 11/14 → 13/14 | 94/151 → 105/151 | 19/50 → 23/50 | 1 → 0 | 132 → 128 |
| Development perspective | 9/14 → 13/14 | 66/151 → 106/151 | 10/50 → 23/50 | 2 → 1 | 141 → 128 |
| Reserved originals | 2/4 → 4/4 | 18/65 → 36/65 | 4/26 → 5/26 | 0 → 0 | 61 → 60 |

| Dataset | No raw reading (from failed registrations) | Wrong raw clock | Invalid raw text | Correct clean blanks | Crossed-out cells flagged |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development originals | 11 (11) → 0 (0) | 7 → 6 | 32 → 35 | 189/189 → 189/189 | 14/30 → 30/30 |
| Development dimmed | 19 (17) → 6 (4) | 9 → 7 | 29 → 33 | 139/189 → 165/189 | 14/30 → 30/30 |
| Development perspective | 57 (57) → 4 (4) | 7 → 7 | 21 → 34 | 130/189 → 165/189 | 14/30 → 30/30 |
| Reserved originals | 28 (28) → 0 (0) | 1 → 3 | 18 → 26 | 10/28 → 24/28 | 6/14 → 14/14 |

The candidate flagged four clean reserved blanks for review. Two dimmed
development punches were detected as blank in both versions. The candidate
issued one wrong hint on a readable perspective variant. It issued zero
hints on blanks, crossed-out cells, or entries labeled ambiguous or
overwritten, and populated zero single-pair punch fields. Registered
development originals had 110 exact readings and 25 correct hints with
either crop method. The original-pixel crop removed the one unsafe hint and
reduced wrong formatted readings from seven to six, with one more invalid raw
reading.

Visual checks on selected recovered development sheets confirmed the 14-row
layout and both punch columns. Some writing touches or crosses the printed
rules, so crop edges can still clip a suffix or retain a neighboring stroke.
The reserved exact result is 55.4%. Independent label review and a fresh
writer-disjoint benchmark are needed to measure progress toward 98%.

### Verification and next run

The full Linux suite passed **129 tests with zero skips**, including the
desktop import, review, approval, export and restart workflow. The
network-blocked OCR and workbook self-test passed. Three public legacy
fixtures produced the same 62 imported punches as v0.5.2. In one serial Linux
run those fixtures took 48.8 seconds with the new single-pair detection
fallback, up from 20.2 seconds. The private benchmark used Tesseract 5.3.4,
OpenCV 4.14.0.94, Pillow 11.3.0 and ONNX Runtime 1.31.1 under the existing
offline guard.

[Payroll Windows job #29](https://circleci.com/gh/nathancspeed67401/HotelPayrollAssistant/29)
passed for the exact frozen OCR source. The Windows Server 2022 job builds
and silently installs the setup, runs the installed model and desktop
workflows, then verifies silent uninstall. The private artifact listing
returned HTTP 404. Use the job's signed-in **Artifacts** tab for
`Windows-Setup/HotelPayrollAssistant_Setup.exe`,
`Verification/installer-sha256.txt` and `Verification/source-commit.txt`.
The setup bytes and checksum still need an independent download check.

To reproduce, install the repository dependencies and fetch the pinned
public model with `python scripts/fetch_ocr_model.py`. Scan from the baseline
and frozen commits. Score both sets with the frozen evaluator for the same
counters. Use a separate `PRIVATE_DIR` for each run and keep the manifest
and originals private. Set `FROZEN_WORKTREE` to the checkout of the frozen
commit. Set `SPLIT=development` and `VARIANT=original`, `dim`
or `perspective` for the development comparisons. Use `SPLIT=holdout` and
`VARIANT=original` for the frozen reserved comparison.

```sh
python experiments/scan_real_forms.py --manifest "$MANIFEST" \
  --originals "$ORIGINALS" --source-sha "$(git rev-parse HEAD)" \
  --split "$SPLIT" --variant "$VARIANT" --output "$PRIVATE_DIR/predictions.json"
python "$FROZEN_WORKTREE/experiments/evaluate_real_forms.py" --manifest "$MANIFEST" \
  --split "$SPLIT" --predictions "$PRIVATE_DIR/predictions.json" \
  --output "$PRIVATE_DIR/summary.json"
```

### Next OCR comparison

Independently check the annotations, then classify the 35
invalid and six wrong raw readings on the registered development originals by
faint stroke, cell-edge spill or recognition error. Use those categories to
select one new crop or preprocessing comparison on the development split.
Freeze it before evaluating newly collected, independently labeled,
writer-disjoint sheets.

## v0.5.2 integrated code

[PR #4](https://github.com/nathancspeed67401/HotelPayrollAssistant/pull/4) preserves both [PR #2](https://github.com/nathancspeed67401/HotelPayrollAssistant/pull/2)
and [PR #3](https://github.com/nathancspeed67401/HotelPayrollAssistant/pull/3) histories. This session verified the previous
[checkpoint](https://github.com/nathancspeed67401/HotelPayrollAssistant/blob/be351f8462f33337cf401328a3a46ffee5f807a8/DEVELOPMENT_PROGRESS.md)
and continued on the same branch.

| Commit | Verified change |
| --- | --- |
| `7c51795` | Keep calculations in integer minutes through weekly, biweekly and workbook totals. Preserve a valid backup if the current session has malformed data. |
| `4207672` | Recover single-pair forms when whole-page text OCR misses the headings. Fit both weeks to observed printed rules and verify the two rectified heading bands before cropping. Count missing minutes and ambiguous entries separately in the private benchmark. |
| `bb467ff` | Keep previously reviewed source images intact across reimports. Reattach identical repaired source bytes, deduplicate recovered imports, report batch counts and finish durable writes before closing. Exercise actual photo and PDF batch import in the installed smoke test. |
| `a9b6414` | Leave single-pair punch fields empty on import. Show OCR suggestions as per-field actions that require an explicit manager choice. Row review and sheet approval are still separate. |

The exact source commit for the candidate is `a9b641417350c621858ef07ab748a28d38df7ac0`.
The full suite passed **122 tests with zero skips** on Linux with a 1366×768
virtual display and kernel-blocked external network access. It exercised real
pinned ONNX recognition, photo and PDF import through the desktop queue,
duplicate prevention, manual edits, all-row review, approval, workbook export
and restart. OpenPyXL independently checked the stored daily, weekly and
grand-total values and the Friday/Saturday midnight boundary. The separate
network-blocked OCR and workbook self-test also passed. A separate offline scale check batch-imported 40 fictional photos, reviewed 560 rows through the review API, independently read 320 elapsed hours in Excel, and recovered all 40 approvals after restart.

## Private photo evidence

All 19 hash-pinned original photographs now have 28 first-pass visual labels
each. The previous 196 labels and the split remain intact. There are 14
development sheets, four frozen reserved sheets and one historical development
sheet. A second reviewer has yet to check any of the 532 labels. The benchmark
excludes ambiguous, corrected and unreadable cells from the exact transcription
denominator and still checks them for unsafe suggestions.

| Dataset | Registered | Exact raw | Correct hints / eligible written | Written without a correct hint |
| --- | ---: | ---: | ---: | ---: |
| Development originals, starting code | 10 / 14 | 96 / 151 | 20 / 50 | 131 |
| Development originals, v0.5.2 | 13 / 14 | 101 / 151 | 22 / 50 | 129 |
| Development originals, dimmed | 11 / 14 | 94 / 151 | 19 / 50 | 132 |
| Development originals, perspective warp | 9 / 14 | 66 / 151 | 10 / 50 | 141 |
| Frozen reserved originals, v0.5.2 | 2 / 4 | 18 / 65 | 4 / 26 | 61 |

On development originals, 11 written cells produced no raw reading, seven
produced a wrong formatted clock and 32 produced invalid text. Of the 219
blank or crossed-out cells, 189 clean blanks were identified and 14 of 30
crossed-out cells were flagged for review. One overwritten entry got a visible
hint. The dim and perspective runs each produced one wrong hint on a readable
entry. The candidate **prefilled zero punch fields** on the single-pair forms
in these runs. The manager still reviews every row. The provisional reserved
result remains 27.7% exact raw, far below the 98% target. There is no independent
writer-level accuracy claim. The low-light and perspective runs are variants
of development photos and do not add independent samples. A separate offline
probe rectified clock cells directly from original-resolution pixels. It
also produced 101 exact raw readings and 22 correct hints on the same
development set. The overwritten-entry hint was absent in that probe. The
application keeps its current crop method pending a new frozen comparison.

## Windows package

[Windows job #27](https://circleci.com/gh/nathancspeed67401/HotelPayrollAssistant/27) reported **passed** for `a9b641417350c621858ef07ab748a28d38df7ac0` through GitHub's exact-commit status. The intermediate [job #26](https://circleci.com/gh/nathancspeed67401/HotelPayrollAssistant/26) passed on `bb467ffb7cbe951899823bbf535a2ca2f70b99bd`. See [Build status](BUILD_STATUS.md) for the earlier known good build.

The pipeline uses the existing payroll-specific CircleCI job, PyInstaller and
Inno Setup. It bundles the integrity-checked offline ONNX weights and Tesseract,
runs the Windows test suite, compiles and silently installs setup, runs the
installed recognition and desktop workflows, then silently uninstalls and
checks that the application executable was removed. The Windows runner is
Server 2022. Lynnette's Windows 10/11 acceptance is still required.

The expected artifact is `Windows-Setup/HotelPayrollAssistant_Setup.exe`.
The job also produces `Verification/installer-sha256.txt` and
`Verification/source-commit.txt`. Access to the earlier private CircleCI
artifact listing returned HTTP 404 without an authenticated project token.
A GitHub commit status establishes the job outcome only. Use the named job's
**Artifacts** tab while signed in with payroll project access.

## Remaining acceptance and OCR work

1. Use the verified job #31 setup for the supervised install, offline
   workflow and uninstall on Lynnette's Windows PC with fictional forms.
2. Get a second visual pass of the private annotations. Keep the reserved
   originals, cleaned copies and augmentations in the same frozen split. Build
   a fresh writer-disjoint evaluation before relying on results for release.
3. Run the next OCR comparison above using the private development split and
   keep the already scored reserved sheets separate.
4. Use the Saturday–Friday printed weeks and the existing overnight entry
   convention. Get the payroll owner's approval of the reconciled workbook
   and the policy decisions listed above.

Keep original employee scans, private labels and detailed predictions outside
Git and CI. The versioned private checkpoint contains the current manifest and
aggregate results. No employee data is required to run the repository tests.
