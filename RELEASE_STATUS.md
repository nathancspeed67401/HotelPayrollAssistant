# Release status · November 7, 2026

**v0.5.2 is an engineering candidate for supervised testing. Live payroll
approval remains open.**

See [Development progress](DEVELOPMENT_PROGRESS.md) for source and verification,
and [Build status](BUILD_STATUS.md) for the exact Windows build.

## Supervised desktop test

1. On a test Windows account, download the candidate setup from the build's
   **Artifacts** tab, keep the desktop shortcut selected, and launch the app.
2. Select **Add Photos / PDFs** and pick fictional time sheets. Enter the
   employee name and the first Saturday of the 14-day payroll period.
3. Compare the original image and the selected row. Choose **Use** only when
   the displayed suggestion matches the source. Enter a confirmed time with
   AM/PM or explicit 24-hour notation. Use **Blank / crossed out** to clear a
   marked cell only after checking the original.
4. Use **Checked: Save & Next** on all 14 rows. **Approve This Sheet** then
   enables export once every employee is ready. Close and reopen the app to
   verify that the working payroll is saved.
5. Open the Excel workbook and check the summary and dated detail rows.
   Elapsed punch hours come from exact minutes. Estimated regular and overtime
   hours still need the hotel's verified workweek and payroll policies.

Before live use, confirm the hotel's payroll rules, independently check the
real-photo accuracy and get Lynnette's acceptance on her Windows computer.
