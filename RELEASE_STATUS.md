# Release readiness update — v0.3 — October 28, 2026

**BLOCKED for boss release.** 31 unit tests pass locally; Windows installer has not been built or installed in CI; the real handwritten scan still produces 0 usable punches. The new genuine-digit-composite test increases exact OCR from 13/66 to 34/66. This is not enough for reliable payroll. See HANDWRITING_BENCHMARK_REPORT.md.

---

# Hotel Payroll Assistant v0.2 — Release status
Date: 2026-10-28

## Not approved for boss deployment yet

This is a **tested development release**, not a verified Windows installer. No Windows installer (.exe) was generated or executed in this environment. The available CircleCI connectors are restricted to other project-specific CI environments and cannot build this payroll project directly. A fresh CircleCI Windows build configuration and a GitHub Actions Windows build workflow are included, but neither pipeline has run for this project.

## Passed

- 28 Python regression tests: payroll math, multiple separate workweeks, midnight/overnight, split shifts, incomplete punches, invalid time formats, duplicate employee, no-export-unapproved, 14-row review gate, local photo archive, review blocked if original image missing, Excel name-as-text safety, saved sessions, PDFs and workbook export.
- Local application `--self-test`: offline Tesseract program launches, payroll calculations and Excel generation complete.
- Linux virtual-display GUI startup smoke test.
- Linux virtual-display **full GUI workflow** with fictional data: open image, confirm 14 days, approve, export a valid KC XLSX.
- CircleCI YAML syntax parsed; Windows configuration authored, but no Windows execution completed.

## Not passed / unverified

- **Automatic handwriting recognition accuracy remains unacceptable on actual handwritten timesheets.** Baseline Tesseract successfully read 103/129 (79.84%) synthetic printed-font times. On the one real handwritten form shared, it read **0 valid punches** and 0 usable names; 28 cells required review. Another local preprocessing attempt still failed to read them reliably. No improved OCR accuracy is claimed.
- Full Windows installation, bundled Tesseract model startup and Windows UI smoke tests not run.
- No code signing; Windows SmartScreen may warn about unsigned installers.
- Overtime is an **estimate based on the printed Saturday–Friday form sections** and must be reconciled with the hotel's actual official workweek.

## Changes in v0.2

1. Local archived image per imported page. Moving phone photos or deleting an original PDF no longer breaks review.
2. Mandatory explicit confirmation of all 14 rows, including blank rows, before approving any sheet.
3. Release-candidate safeguard: old saved approvals without row-by-row verification are revoked on session load.
4. Enlarge selected handwriting row in a separate window.
5. Enter payroll period once; other currently blank sheets inherit it.
6. Prevent spreadsheet-formula injection through employee names.
7. CLI `--self-test` for verifying packaged software on a Windows machine.
8. CircleCI Windows machine executor and GitHub Actions builder both compile installer **and** perform a silent-install/self-test before publishing an artifact.

## Requirements before handing to the manager

- Set up a **private repository** for this project and run the Windows CI builder; download a real `HotelPayrollAssistant_Setup.exe` artifact.
- Run the installer on a regular Windows laptop, not only the CI machine. Validate startup and uninstallation.
- Test OCR on a representative collection of independently verified genuine handwriting and phone images. Require visual review of **every** timesheet. OCR isn't guaranteed correct even at a high benchmark score.
- Confirm KC's required report fields, especially overtime workweek definition, before using for actual wages.

**Do not hand this source ZIP to the manager as if it were the finished installer.** It is intended for engineering/testing until these release gates pass.
