# Release status · November 7, 2026

| Release gate | Status |
| --- | --- |
| Ready for a supervised install with fictional data | Yes. The job #31 installer checksum and source commit match. |
| Ready for live payroll | Pending fresh handwriting acceptance, installer verification for the release source, Lynnette's Windows test and payroll owner approval |

See [Development progress](DEVELOPMENT_PROGRESS.md) for OCR evidence and
[Build status](BUILD_STATUS.md) for exact Windows job and artifact identity.
The job #32 handwriting candidate read 40 of 65 reserved punches exactly.
Its Windows build passed and the installer file still needs verification.
The supervised test can use the verified job #31 setup and the fictional pack.

## Lynnette's Windows acceptance

Use the verified setup, the fictional acceptance pack and a separate Windows
test account on Lynnette's PC. Use November 7, 2026 as the first Saturday.

1. Confirm the setup SHA-256 with `Get-FileHash` and compare the source
   manifest with the passing job. Install, launch and disconnect the PC from
   the network for the workflow checks.
2. Select **Add Photos / PDFs**. Import the 30 fictional sheets from the
   pack, including the missing-punch PDF. Check that the app opens every
   original and keeps punch fields empty until a manager enters or accepts a
   time. Check each employee name and set the first Saturday. Use the filename
   labels as employee names for this test.
3. Compare each time with its source. Select **Use** only for a matching
   suggestion. Confirm a blank or crossed-out entry explicitly when prompted.
   Check that the missing clock-out blocks the row, then enter the fictional
   correction of **1:00P** for Test 02, first Saturday. Use
   **Checked: Save & Next** for all 14 rows, then **Approve This Sheet**.
   Verify export is blocked while any sheet is unapproved.
4. Close and reopen the app during review. Confirm that photos, partial
   corrections and approvals reappear. Finish the review, export Excel and
   reconcile the dated rows and totals below.
5. Uninstall from Windows, check that the app and its shortcut are gone, and
   record the Windows version, installer SHA-256 and each step's result.

| Fictional employee | Week 1 | Week 2 | Check |
| --- | ---: | ---: | --- |
| Test 01 Overnight | 40 h 01 m | 7 h 59 m | Friday 11:00P–7:01A stays in the first printed week. The 12:00A start stays on its written row. Expect one overtime minute. |
| Test 02 Missing Punch | 5 h | 5 h 01 m | The first row requires the confirmed correction. For this fictional housekeeper, only the longer day requires a 15-minute break review. |
| Tests 03–29 Day Shift | 8 h 05 m each | 10 h 02 m each | Treat these employees as other roles for the break review. |
| Test 30 Split Shift | 40 h | 24 h | 8:00A–12:00P and 1:00P–5:00P total 8 hours on each worked day. |
| All 30 employees | 303 h 16 m | 307 h 54 m | 611 h 10 m elapsed, including one overtime minute in the printed weeks. |

The two Saturday–Friday printed weeks are the app's calculation basis.
Enter overnight punches on the row written by the employee, including the
hotel's midnight-start convention. Excel totals use exact elapsed minutes and
display decimal hours. Review the 15-minute break requirement separately for
housekeepers working more than five hours in a day. The calculation uses
actual punches with zero automatic break deductions. Confirm the treatment
of any separate meal rule, payroll rounding or exact-minute totals, and the
reconciled workbook with the payroll owner before live use.
