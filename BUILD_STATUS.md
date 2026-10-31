# Build status — October 30, 2026

The previous PDF-test fix was verified by CircleCI Windows job 5 on commit
`4c9fe5c11b10b527827061efbdbd0b4dafb29381` and merged to main as
`3f55ec2f7305b7bfa9391b6edcf17b01df8454be`. That success predates the new
whole-entry recognition engine and does not verify this changed installer.

Current local verification: 63 tests passed, three GUI tests skipped because
this Linux session has no display. The application self-test passed under an
outbound-network deny filter, exercising the actual pinned ONNX model, digit
model, Tesseract, payroll math, and Excel export. A Python 3.12 Windows x64 wheel
for the pinned ONNX Runtime 1.31.1 dependency was also confirmed available.

The Windows workflow now downloads and verifies the public handwriting model
before tests, collects ONNX Runtime in PyInstaller, bundles model attribution
and licensing, and executes the real ONNX graph in the installed self-test.
It also silently installs the Inno Setup build and opens/closes the installed
GUI. Artifacts record the source SHA, dependency versions, installer hash, and
test results.

A fresh Windows result for this changed tree is pending. The handwriting
engineering build remains for supervised testing. Its measured development
results are in `HANDWRITING_BENCHMARK_REPORT.md`; it still misses five of sixteen
unambiguous punches on the one original handwritten scan.
