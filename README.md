# Hotel Payroll Assistant — v0.3 OCR Engineering Build

**NOT YET READY FOR LIVE PAYROLL OR THE MANAGER'S WINDOWS LAPTOP.**

Latest held-out real-digit-composite benchmark: **34/66 exact punches (51.52%)**; original handwritten employee example still yields no usable entries. See [HANDWRITING_BENCHMARK_REPORT.md](HANDWRITING_BENCHMARK_REPORT.md).

All entries require visual review and sign-off. The source ZIP contains the OCR model, test forms, known answers, offline test scripts, and an unexecuted Windows installer build pipeline.

---

# Hotel Payroll Assistant — Windows development build (v0.2)

A simple desktop tool for **unchanged, handwritten, two-week paper timesheets**.
It imports phone photos and scanned PDFs, attempts local OCR, keeps a private local copy of the original image, shows the **image next to editable punches**, totals hours, and exports an Excel report for Kansas City. All timesheet images stay on the laptop.

## For the hotel manager (after installer is built)

1. Double-click `HotelPayrollAssistant_Setup.exe` and follow **Next → Install**. Use the new desktop shortcut.
2. Take readable, straight-on photos of the existing paper timesheets using the phone's document-scan mode. Transfer the images to the laptop using Quick Share, USB, or email.
3. Open **Hotel Payroll Assistant**, click **Add Photos / PDFs**, and select the photos.
4. **Check every row against the photo on the right**, including blank days and the employee name. Click a day, correct the boxes, and **Checked: Save & Next**; confirm all 14 rows, including blank days.
5. Enter the **first Saturday's date** of the biweekly pay period in `MM/DD/YYYY` form (e.g., `10/24/2026`). Enter it once; the app copies it to the other timesheets.
6. Click **Approve This Sheet**; repeat for each employee. The app will not export until all sheets are approved.
7. Click **Export Excel**. Review the resulting `PAYROLL SUMMARY` and email the workbook to KC.

**Overnight convention:** A shift entered on Tuesday stays in Tuesday's row even when its clock times cross midnight. `11P → 7A` is eight hours on the paper day. `12A → 8A` is also eight hours on its paper day. The application NEVER silently shifts that row's hours to another day.

**Important overtime caveat:** The Excel report shows **preliminary** weekly overtime totals using the two Saturday-to-Friday sections on the paper. Federal overtime is based on the employer's actual fixed 168-hour workweek; payroll personnel must reconcile any differences, particularly shifts crossing the official boundary. The program is NOT a legal compliance engine.

## Accuracy and project status

**Version 0.2 is a tested development build, not a verified Windows installer or production-ready OCR solution.** See `TEST_REPORT.md` for the complete 10-form synthetic and real-scan spot-check results.

* OCR uses open-source Tesseract with the fixed regions of the supplied form. Tesseract often reads handwritten numbers and AM/PM letters incorrectly. On 10 synthetic printed-font sheets it recognized only **103/129 (79.84%)** punches exactly. On the real sample, it parsed **zero** clock times successfully. This is currently *insufficient to automate payroll data entry reliably*.
* The review step is mandatory; no unapproved sheet exports. The app does not automatically infer AM/PM or fill missing punches.
* Mobile document-scan mode is strongly recommended: skewed / differently cropped photos can misalign the fixed OCR regions. Test against several actual completed sheets before relying on it.
* Employee pictures and signatures are excluded from the exported payroll workbook. All processing is offline once installed.
* Both CircleCI and GitHub Actions Windows installer pipelines have been authored. Neither has been executed for this project; a tested `.exe` is not included in this ZIP.
* Signed paper sheets must be retained per workplace policies.

## Developer: run from source

Requires Python 3.12+ and **Tesseract OCR 5** executable installed locally.

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
python -m pytest -q
python main.py
```

On Windows `tesseract.exe` can be found at `C:\Program Files\Tesseract-OCR\tesseract.exe`.

## Developer: generate a one-click `.exe` Windows installer

The included `.github/workflows/windows-installer.yml` is configured to run on a GitHub-hosted **Windows runner**. Upload this source to a private GitHub repository, choose **Actions → Build Windows Installer → Run workflow**. Once build succeeds, download the `HotelPayrollAssistant-Windows-Setup` artifact, extract it, and give the `.exe` to the manager. This Windows installer bundles the Python application **and the Tesseract engine**, and does not require Python or Tesseract preinstallation on her laptop. The installer itself does not require administrator privileges.

If a build fails due to a runner package version change (Chocolatey or Inno Setup), inspect the workflow log before distributing the installer. Antivirus may flag an unsigned installer; code signing is outside this prototype's scope.

## App architecture

- `app/core.py` — deterministic time normalization, overnight shifts, validation, week totals, separate >40-hour weekly OT.
- `app/ocr.py` — local Tesseract, 14-row fixed-form extraction, scanned PDFs.
- `app/ui.py` — Tkinter interface, local autosave, photo reference, approval gating.
- `app/report.py` — `.xlsx` export with per-employee summary and 14-day details.
- `tests` — 24 automated payroll / import / export tests, fictional sheet generator and OCR evaluator.
- `test_samples` — 10 fictional test sheets and benchmark results. See `TEST_REPORT.md`.
- `installer` — Inno Setup project for no-admin per-user installation.

## Data/privacy

The app saves its in-progress session under `%LOCALAPPDATA%\Hotel Payroll Assistant\current_session.json` and doesn't upload data anywhere. The original photos remain wherever your boss placed them. The session stores employee names, times, paths to source photos, and approvals; protect the Windows account and laptop appropriately. To clear a session, click **New Pay Period**. Imported image copies are retained under the per-user scans folder to preserve audit evidence; a manager must maintain a local retention policy. There is no centralized database or password feature.

## Limitations/next milestone

- Improve handwriting recognition and image alignment for real phone captures. The initial sample demonstrates how poorly Tesseract reads certain handwritten punches.
- Run hands-on Windows installer smoke tests and 10–20 independently verified real paper sheets; measure field-level recognition accuracy.
- Confirm the employer's fixed overtime workweek and the exact emailed report columns required by KC.
- Add an export preview and optional date picker to reduce manual entry.

**Do not use unreviewed OCR-derived numbers to process wages.**

## CircleCI Windows build

See `.circleci/config.yml`. Upload this project to a private GitHub repo connected as its own CircleCI project, then run the `build-release` workflow. It installs Python, Tesseract and Inno Setup on a Windows executor, runs tests, builds the app and installer, installs it silently, runs `--self-test`, and stores the setup `.exe` as a CircleCI artifact. The currently connected CircleCI tools for other projects cannot directly run this configuration. CircleCI Windows usage may consume CI credits.

## v0.2 safety improvements

All 14 printed rows must be saved as explicitly reviewed before approval, including blank rows. The selected handwriting can be enlarged, and a local archived image survives the original phone picture being moved or deleted. No OCR-derived punch is considered verified until visually compared with the paper form. See `RELEASE_STATUS.md`.
