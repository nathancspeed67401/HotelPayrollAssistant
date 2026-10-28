# Handwriting benchmark provenance

- Public corpus: scikit-learn bundled `load_digits()` (UCI Optical Recognition of Handwritten Digits), containing 1,797 real human-written 8×8 digit samples.
- Only samples with index 1100 onward were used to assemble these test forms.
- Clock times, line layout, employee names, AM/PM suffixes and punctuation were generated. Digits are **genuine but resized and synthetically recombined**; no person physically wrote these complete timesheets.
- No real employee personal data or times are included.
- The visual layout matches the same two-week form geometry; this is a re-created blank form, not an unmodified scan.
- Treat accuracy as regression on this narrow sample; do not use it as a claim of real phone-photo or whole-timesheet accuracy.
- Source: https://archive.ics.uci.edu/dataset/80/optical%2Brecognition%2Bof%2Bhandwritten%2Bdigits and https://scikit-learn.org/stable/modules/generated/sklearn.datasets.load_digits.html
