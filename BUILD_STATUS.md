# Build status — October 30, 2026

CircleCI Windows installer job 8 passed for the new handwriting reader:
https://circleci.com/gh/nathancspeed67401/HotelPayrollAssistant/8

Tested source commit: `7a242619cb55b5d30f70be42a7f87b1806df7774`.
Tested source tree: `4880975bb8c3fcc9eb63c3b3c457ee737655d8cf`.

The successful Windows workflow downloaded and SHA-256 verified the pinned
public model, ran the automated tests (including Windows GUI tests), built the
Inno Setup installer, silently installed it, exercised the installed ONNX,
digit model, Tesseract, payroll calculation and Excel export paths, and opened
and closed the installed GUI. Its artifacts include verification records and
`Windows-Setup/HotelPayrollAssistant_Setup.exe`.

The green status was retrieved through GitHub. The installer binary and
individual CircleCI logs/artifact listing have not been downloaded in this
session; a normal Windows laptop has not been tested here.

Local verification: 63 tests passed, three GUI tests skipped for lack of a
display. The real-model installation/export self-test also passed under an
outbound-network deny filter. The final documentation/research follow-up does
not change the application, dependencies, tests, CI workflow, or installer
source from the tested commit above.

Handwriting reliability remains incomplete: 11 of 16 unambiguous punches were
recovered on the original development sheet; five need manual entry and two
additional punches omit AM/PM. All 14 rows require review before approval.
See `HANDWRITING_BENCHMARK_REPORT.md` for measured development results and
`experiments/RESEARCH_NOTES.md` for excluded experiments.
