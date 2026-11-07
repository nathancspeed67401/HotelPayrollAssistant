# Development progress · November 7, 2026

**v0.5.2 engineering candidate. Keep it out of live payroll.**

## Integrated code

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

## Resume here

1. Retrieve setup and the verification files from the exact candidate job.
   Check the SHA-256 against the downloaded bytes and run an install, offline
   use and uninstall on Windows 10/11 with fictional forms.
2. Get a second visual pass of the private annotations. Keep the reserved
   originals, cleaned copies and augmentations in the same frozen split. Build
   a fresh writer-disjoint evaluation before relying on results for release.
3. Reproduce tall-header and low-light registration failures on development
   photos. Require observed printed evidence for all 14 rows and abstain on
   unresolved geometry. Improve raw OCR and use the scorer to measure missed
   writing, unsafe hints and manual entries.
4. Confirm the employer's actual workweek boundary, time conventions, meal
   deductions and rounding with the payroll owner. The workbook measures
   elapsed punch minutes and labels Saturday–Friday regular/overtime estimates
   as preliminary. [U.S. Department of Labor workweek guidance](https://www.dol.gov/agencies/whd/fact-sheets/23-flsa-overtime-pay)

Keep original employee scans, private labels and detailed predictions outside
Git and CI. The versioned private checkpoint contains the current manifest and
aggregate results. No employee data is required to run the repository tests.
