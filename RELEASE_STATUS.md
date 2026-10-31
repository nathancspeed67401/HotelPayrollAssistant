# Release state — v0.4 engineering build — October 30, 2026

The new local whole-entry reader and printed-grid alignment recover 11 of 16
unambiguous punches on the original development sheet, with zero incorrect
filled times observed. Five still need manual entry; two additional entries
lack AM/PM and remain unresolved. This is an improved supervised engineering
build, not completed automatic handwriting recognition.

The composite benchmark improved from the historical 34 correct/10 wrong to
36 correct/zero wrong of 66. The printed-font set now reads all 128 unambiguous
punches and leaves its one ambiguous entry empty. Blank cells remain empty in
these development checks. These results do not validate other writers.

All 14 rows still require explicit visual review. Sheet approval, valid punch
pairs, a valid pay-period date, an employee, and the archived original are
required before export. No OCR suggestion finalizes pay.

63 local tests and the offline real-model self-test pass; three local GUI tests
are skipped for lack of a display. A fresh Windows installer run is pending;
see `BUILD_STATUS.md`. Do not represent the previous successful build as a
verification of this new recognition engine.
