# Development progress · November 8, 2026

**Engineering candidate based on v0.5.2. The installer is verified for supervised testing with fictional data. Live payroll acceptance is open.**

## Faint handwriting review

The offline importer now flags coherent faint strokes when the usual ink
check would classify the cell as blank. The reviewer must enter a time or
confirm the blank or crossed-out field. The faint-ink check supplies no
transcription, suggestion or field value.

On a fictional full-sheet import, all 16 faint punches went from blank
to explicit review. All 12 blank, speckle and dash controls stayed blank.
Separate controls kept all 20 clean suggestions and withheld suggestions
on all 32 conflicting AM/PM and all four missing AM/PM examples. The
offline Linux headless suite passed 155 tests and the application self-test.

The baseline was draft head `c788d5817d6509aad3cb77f2f6a1246e15f43420`.
The frozen code and test tree was `95a819066826611b5b88c741030a7c69b460cc9d`.
Both ran the same offline import path, pinned models and scorer. All
scored counters matched.

| Photo set | Exact literal reads | Correct complete suggestions | Manual entries | Wrong raw reads | Unsafe suggestions |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development originals | 115/151 | 32/50 | 119 | 5 | 0 |
| Development dimmed | 116/151 | 29/50 | 122 | 7 | 0 |
| Development perspective | 117/151 | 30/50 | 121 | 8 | 0 |
| Reserved originals | 40/65 | 7/26 | 58 | 3 | 0 |

There were zero autofilled punches and no additional clean blanks flagged
for review. The four reserved originals were scored in aggregate after the
candidate was frozen. Production accuracy still requires fresh,
writer-disjoint photos with independently checked labels.

Character-position alignment between the two readers recovered two exact
reads on development originals and added no complete suggestions. A dimmed
correction cell produced a plausible raw clock despite agreement across
two views of the first reader. Alignment stays experimental.

Next, test whether the disputed glyph contains overlapping or separate
correction strokes before counting matching positions as corroboration.
Start with controlled overwrites and naturally joined clean glyphs. Then
compare literal recovery and correction errors on development originals
and dimmed photos. Keep the whole-clock requirements for suggestions.

## Dense short cancellation strokes

A dense clock entry can obscure one side of a short strike-through. The
single-pair importer now withholds a suggestion in that case only when a
nearly horizontal, continuous stroke intersects at least four separated
ink groups, has a visible tail beyond the outer crossings, and passes
through a clear interval on one side. The cell remains available for
manual review.

The last of four fictional short cancellations went from a suggestion to
manual review. All 12 clean, underlined and printed-edge controls kept their
correct suggestions. The offline Linux headless suite passed 154 tests and
the application self-test, including the blank, crossed-out and conflicting
time cases.

The baseline was draft head `8b10b78129801ff9ac9e49e33d123f2b8261a313`.
The frozen code and test tree was `2eb5df35723bf8d3c81391b58643d8a2e8cffc26`.
Both used the same offline import path, pinned models and scorer. All
private benchmark counters matched.

| Photo set | Exact literal reads | Correct complete suggestions | Manual entries | Wrong raw reads |
| --- | ---: | ---: | ---: | ---: |
| Development originals | 115/151 | 32/50 | 119 | 5 |
| Development dimmed | 116/151 | 29/50 | 122 | 7 |
| Development perspective | 117/151 | 30/50 | 121 | 8 |
| Reserved originals | 40/65 | 7/26 | 58 | 3 |

Every private run recorded zero unsafe suggestions and zero autofilled
punches. The four reserved originals were scored in aggregate after the
candidate was frozen. Production accuracy still requires fresh photos
from different writers and independently checked labels.

The printed-divider experiment masked neutral vertical rules only inside
the registered crop. The fictional checks kept colored pen pixels. The
strict mask recovered two exact reads on the perspective variants.
One of those reads had matching unaltered alternate-reader evidence.
There was no gain on originals or dimmed photos under the strict mask.
The relaxed mask added one exact read on dimmed photos and one wrong raw
read plus an ambiguous-cell read on originals. Neither mask improved
complete suggestions.
A separate check requiring alternate-reader corroboration of a single
visually confusable character also recovered no reads. Both remain
experiments.

Next, map character positions from both readers back to the original crop
and test whether they point to the same ink when they disagree about a
digit or suffix. Compare aligned evidence with current whole-clock
agreement. Test original, faint, crossed-out and neighboring-ink controls
and keep the reserved split for a frozen regression.

## Review-only fallback when the primary reader fails

If the primary model is unavailable, the offline clock reader can now
supply a literal transcription for review when its two scale views agree
and every character clears the confidence floor. The fallback preserves
written minutes and AM/PM exactly as read and excludes detected
strike-throughs. It creates no time suggestion or filled punch.

The frozen code and test tree was `e037d1ada7e13a4f4ec80bc1aad477ae6a290287`.
The baseline was draft head `9bc690704be2b3af803441f81ff17bda2727bff6`.
Both used the same registered import path and unchanged scorer. Pointing
the primary reader at a missing model gave these development results.

| Photo set | Exact literal reads | Correct complete suggestions | Manual entries | Wrong raw reads |
| --- | ---: | ---: | ---: | ---: |
| Development originals | 0/151 → 4/151 | 0/50 | 151 | 0 |
| Development dimmed | 0/151 → 7/151 | 0/50 | 151 | 0 |
| Development perspective | 0/151 → 6/151 | 0/50 | 151 | 0 |

The fallback improved literal transcription during the simulated outage.
Every outage run had zero unsafe suggestions and zero autofilled punches.
A lower threshold produced wrong raw reads on development originals.

With both readers present, all counters matched the baseline.

| Photo set | Exact literal reads | Correct complete suggestions | Manual entries | Wrong raw reads |
| --- | ---: | ---: | ---: | ---: |
| Development originals | 115/151 | 32/50 | 119 | 5 |
| Development dimmed | 116/151 | 29/50 | 122 | 7 |
| Development perspective | 117/151 | 30/50 | 121 | 8 |
| Reserved originals | 40/65 | 7/26 | 58 | 3 |

Every normal run had zero unsafe suggestions and zero autofilled punches.
The four reserved originals were scored in aggregate after freezing the
candidate. Fresh photos from different writers with independently checked
labels are still required for the 98% acceptance test.

The offline Linux headless suite passed 154 tests and the application
self-test. New fixtures cover primary and dual-reader outages,
conflicting times, blank and crossed-out cells, and agreement that
preserves incomplete minutes and AM/PM.

A same-row divider experiment limited outside ink to connected components
that originated inside the punch and matched its pen color. It admitted
three original-development crops and recovered zero reads or suggestions
across the original, dim and perspective runs. A general disagreement veto
also withheld valid suggestions and was discarded.

Next, measure whether a residual printed divider inside the registered
crop is read as a digit. Test a local rule mask that uses printed geometry,
retains colored pen ink, and samples only the original crop. Compare
exact reads, complete suggestions, and wrong reads on development photos
and include neighboring ink, blank and faint-pencil controls.

## Short cancellation strokes and blur experiment

The single-pair importer now also checks for a short, continuous stroke
that intersects two separated ink groups and remains visible in the space
between them. The check runs only on proposed punches. It withholds the
suggestion and leaves the raw text and cell available for manual review.

On the four short fictional cancellations that remained at draft head
`0485d5ee4175a5cee7f289de9e033e2907dca222`, suggestions fell from four to
one. All 12 clean, underlined and printed-edge controls kept their
suggestions. The remaining fictional mark lacked a clear gap between
crossings. The real-reader integration fixture covers three short marks,
blank and dash-only controls, and the required manual review. The offline
Linux headless suite passed 147 tests and the application self-test.

The frozen code and test tree was `c1177f1d4e8efce04d1cad13a29656515042bf6e`.
The offline import path and unchanged scorer matched the verified baseline
on the same photos, labels and pinned model weights.

| Photo set | Exact literal reads | Correct complete suggestions | Manual entries | Wrong raw reads |
| --- | ---: | ---: | ---: | ---: |
| Development originals | 115/151 | 32/50 | 119 | 5 |
| Development dimmed | 116/151 | 29/50 | 122 | 7 |
| Development perspective | 117/151 | 30/50 | 121 | 8 |
| Reserved originals | 40/65 | 7/26 | 58 | 3 |

Every private run had zero unsafe suggestions and zero autofilled punches.
All 30 crossed-out development cells and 14 crossed-out reserved cells
were flagged for review on the originals. The four reserved originals
were scored in aggregate after the OCR code was frozen. A fresh
writer-disjoint set with independently checked labels is still needed
for the 98% acceptance test.

A local blur probe fit horizontal and vertical printed rules beside the
clock cells. It distinguished the two blur directions and defocus on
fictional controls while leaving all 28 sharp controls alone. On the
development originals, 57 of 171 uncertain cells were eligible for
restoration, including 13 literal misses. Bounded sharpening and
regularized inverse filtering each added one exact raw read and one
wrong raw read. A matching unaltered second-reader output recovered no
original or dimmed reads and one perspective-variant read. No tested
policy improved complete suggestions. Blur restoration stays out of the
importer.

Next, test limited recovery across a vertical clock-column divider
within the same row. Use only ink connected to the inside of the
registered punch, exclude the printed divider, and test with neighboring
ink and blank controls. Compare exact reads, correct suggestions and wrong
reads separately before freezing a candidate.

## Withhold suggestions on crossed-out clocks

The single-pair importer withholds a complete suggestion when a nearly
continuous stroke crosses the writing and clock ink remains visible on both
sides. It retains the raw OCR reading and marks the cell for manual review.
Printed row edges are excluded from the supporting evidence.

In two fictional photo probes, suggestions on 32 canceled punches fell from
**29 to 4**. The remaining four had shorter cancellations. A wider detector
caught all four and withheld a correct suggestion on both the original and
dimmed development sets. The candidate uses the narrower detector. It kept
all 16 suggestions on clean, underlined and printed-edge controls. Blank and
dash-only controls received zero suggestions. Two real-reader
import tests cover both printed header layouts, blank cells, underlines,
printed edges and multiple strike styles. The offline Linux headless suite
passed 146 tests and the application self-test.

The baseline is draft head `b1b056a333e96a05d5a340992d5ac73df425c3f5`.
The frozen source and test tree is `ca68e7aac2eda1cca21dbed28b03c2d8a7dfdc7a`.
The same offline import path, pinned weights, original hashes, labels and
scorer produced identical counts in both versions.

| Photo set | Exact literal reads | Correct complete suggestions | Manual entries | Wrong raw reads |
| --- | ---: | ---: | ---: | ---: |
| Development originals | 115/151 | 32/50 | 119 | 5 |
| Development dimmed | 116/151 | 29/50 | 122 | 7 |
| Development perspective | 117/151 | 30/50 | 121 | 8 |
| Reserved originals | 40/65 | 7/26 | 58 | 3 |

Every private run had zero wrong or unsafe suggestions and zero autofilled punches.
All 30 crossed-out development cells and all 14 crossed-out reserved cells
were flagged for review on the originals. The reserved originals were run in
aggregate after freezing the candidate. Independently checked photos from
different writers are still needed for the 98% acceptance test.

Localized suffix masking with an adjacent blank control recovered one
additional exact reading on development originals and also selected a raw
clock on an ambiguous cell. Requiring the independent reader to agree on
the digits produced zero changes across originals, dim and perspective.
A separate check using the bundled isolated-digit classifier also recovered
zero reads on the development originals. Neither experiment is in the
importer.

Next, measure blur on printed rules near unreadable development punches.
Use the rule edges to estimate a direction and width, then test whether
applying a restrained deblur to the original crop corroborates intact clock
reads. Include deliberately blurred and unblurred controls and score
literal reads, complete suggestions, manual entries and wrong reads
separately. Keep the reserved split for the frozen regression.

## Printed-grid retry under uneven lighting

When the printed form header establishes orientation and the first grid
registration fails, the importer retries registration with local illumination
flattened. It uses the same printed rule, weekday and geometry checks.
Punch recognition still receives the original photo pixels.

The baseline is draft head `a71a7395f23d5f724dff9fecc03d110f0bb02063`.
The frozen code and test tree is `ccec223bfcb63e9ad6ab0a12b7976f0e13591fa2`. Both sides
ran the same offline import path, pinned models and scorer. All 19 archived
and extracted original hashes matched the checkpoint manifest.

| Photo set | Registered | Exact literal reads | Correct complete suggestions | Manual entries | Wrong raw reads |
| --- | ---: | ---: | ---: | ---: | ---: |
| Development originals | 14/14 → 14/14 | 115/151 → 115/151 | 32/50 → 32/50 | 119 → 119 | 5 → 5 |
| Development dimmed | 14/14 → 14/14 | 116/151 → 116/151 | 29/50 → 29/50 | 122 → 122 | 7 → 7 |
| Development perspective | 13/14 → 14/14 | 114/151 → 117/151 | 27/50 → 30/50 | 124 → 121 | 7 → 8 |
| Reserved originals | 4/4 → 4/4 | 40/65 → 40/65 | 7/26 → 7/26 | 58 → 58 | 3 → 3 |

There were zero wrong suggestions, zero unsafe suggestions and zero
autofilled punches in both versions. The recovered perspective sheet added
three correct complete suggestions and one wrong raw read that stayed in
manual review. All 30 crossed-out development cells
and all 14 reserved crossed-out cells went to review on the original photos.
The reserved photos were scored in aggregate after freezing the candidate.
Their labels are first-pass. No independently checked writer-disjoint
acceptance set was available.

The offline Linux headless suite passed 144 tests and the application
self-test. Two fictional import tests verify recovery from a shadow,
rejection of a missing row rule, use of original pixels, and review of a
blank cell, a crossed-out mark and conflicting clock readings.

The same-sheet calibration experiment compared alternating rows on the
14 development originals. Eighteen of the 28 calibration folds had a
written AM/PM example. Whole-clock templates changed no reads. Isolated
suffix templates corroborated one additional exact transcription
(115/151 to 116/151), with five wrong reads and 32/50 complete suggestions
in both versions. The reference annotations were first-pass and writer
identity was unverified, so the template experiment stays offline.

Next, test whether masking only the visible suffix region drops A/P
confidence while preserving the numeric read. Compare this signal on
development cells with written A/P, no suffix, and overwritten ink.
Use it only to corroborate a suffix already read from the intact crop.
Measure literal reads and complete suggestions separately and freeze any
candidate before the reserved regression.

## Handwriting OCR checkpoint

The single-pair importer retries the printed weekday labels in a shifted band
when the first crop supplies too few anchors. Either pass rejects contradictory
weekday labels. The native clock crop uses bicubic resizing before line
recognition. Two synthetic regression cases check recovery and rejection when
a weekday is out of order. The tested code and test files are identified by
Git tree `09e9417c882daae2d7f8892de2baa15393ada1f5` before this note.

The baseline is draft PR #5 head `749f6b1bb5cb3322a45e74a6997b9742dfc50c6a`.
Both versions used the same pinned models, original photo hashes, labels,
scorer and offline import path.

| Photo set | Aligned sheets | Exact handwritten reads | Correct complete suggestions | Punches requiring entry |
| --- | ---: | ---: | ---: | ---: |
| Development originals | 14/14 → 14/14 | 114/151 → 115/151 | 32/50 → 32/50 | 119 → 119 |
| Development dimmed | 13/14 → 14/14 | 113/151 → 116/151 | 26/50 → 29/50 | 125 → 122 |
| Development perspective | 13/14 → 13/14 | 114/151 → 114/151 | 27/50 → 27/50 | 124 → 124 |
| Reserved originals | 4/4 → 4/4 | 40/65 → 40/65 | 7/26 → 7/26 | 58 → 58 |

The reserved regression ran after freezing the candidate. The candidate
produced zero unsafe suggestions and zero autofilled punches in these runs.
Wrong raw reads went from six to five on development originals and stayed
at three on the reserved set. The 61.5% reserved exact result uses first-pass
labels. The 98% target still requires independently checked labels and fresh
photos from different writers.

Linux verification with outbound networking blocked passed 142 tests and
the application self-test. This run used the headless suite and deferred
the desktop and Windows build checks to the release workflow.

The experiments with extended crops sometimes included strokes from adjacent
rows. The stricter crop and extra scale variants yielded few safe recoveries.
A clock-constrained decoder produced plausible wrong times without enough
visual evidence. The separate PP-OCRv6 small and English PP-OCRv5 models and
the small clock model fine-tuned on development photos performed worse as
standalone readers. Four photo-grouped validation folds for that fine-tune
produced 112–113 exact reads and 29–30 correct suggestions when combined
with the primary reader, compared with 114 and 32 for the baseline. The
public handwriting-font warm start showed a small transcription gain while
losing suggestions. The draft keeps the existing model weights.

An offline TrOCR small handwriting probe at revision
`b4648cfa171985a6745f37ddd637e98c0da958ac` recovered one of 37 original
development misses across native and tightened grayscale crops. It was also
tested on 17 baseline matches and 11 ambiguous or crossed-out controls.
Two primary views already read the correct numeric portion on 17 of the 37
misses with a written meridiem. Six of those 17 had the correct A or P in at
least one primary output. A public-font suffix classifier with projected
crop boundaries recovered three of the misses and made four wrong guesses.
With the pinned EMNIST Balanced natural glyphs and explicit no-suffix controls,
the corresponding classifier got 1,428 of 1,800 public-glyph examples right.
It recovered three development misses and made five wrong guesses under the
tested agreement threshold. Reading four candidate suffix cuts with the
medium and English line models recovered one extra complete clock when two
views from each model agreed. This was an offline crop experiment.

The next development comparison should test writer-specific visual evidence
from a small set of reviewed clock examples kept locally. Separate the
calibration rows from the scored rows and test on additional sheets when
writer identity can be verified. Measure gains for literal reads and
complete suggestions independently, including no-suffix, corrected and
crossed-out controls. Use the reserved originals only for a frozen regression.

## Clock-specific handwriting reader

The offline second reader in the draft candidate uses a small model trained
on 48,000 fictional clock and noise examples composed from public EMNIST
glyphs. The private timesheets and labels were used to evaluate recognition
and tune the corroboration policy. The bundled model and the test fixtures
contain public or fictional inputs.
[PR #5](https://github.com/nathancspeed67401/HotelPayrollAssistant/pull/5)
· [Tested source](https://github.com/nathancspeed67401/HotelPayrollAssistant/commit/be16f5b5e20c3a608c1aa3531714f335056cfc23)

The offline trainer reproduced the bundled ONNX file byte for byte on Linux
with PyTorch 2.6.0 CPU and ONNX 1.18.0.

```sh
python experiments/train_clock_reader.py --data "$EMNIST_BALANCED" --output "$CLOCK_MODEL"
```

The second reader checks uncertain readings on registered single-pair forms.
A complete suggestion requires both readers to see the same written clock
without a strong conflicting reading. A raw reading with strong character
scores may appear for manual review. A suggested punch requires written
minutes and AM/PM where applicable. Managers enter or deliberately accept
each punch, review every row, and approve every sheet before export.

| Private regression set | Registered | Exact raw | Correct suggestions / eligible | Manual entries | Wrong raw | Invalid raw |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Development originals | 14/14 | 112/151 → 114/151 | 28/50 → 32/50 | 123 → 119 | 6 → 6 | 33 → 31 |
| Development dimmed | 13/14 | 109/151 → 113/151 | 24/50 → 26/50 | 127 → 125 | 7 → 7 | 31 → 27 |
| Development perspective | 13/14 | 108/151 → 114/151 | 24/50 → 27/50 | 127 → 124 | 7 → 7 | 32 → 26 |
| Reserved originals | 4/4 | 39/65 → 40/65 | 7/26 → 7/26 | 58 → 58 | 3 → 3 | 23 → 22 |

Comparisons use the verified job #31 source as the baseline. All runs had
zero wrong or unsafe suggestions, zero false blanks on readable punches and
zero suggestions on crossed-out entries. Each distorted run missed four
readable punches on a sheet that failed registration. Five clean blanks
on the reserved originals went to review. Manual entries count readable
punches without a correct complete suggestion. The reserved exact result
was 61.5%. The 98% acceptance gate still requires fresh writer-disjoint
photos with independently checked labels. All 19 original hashes matched
the checkpoint with its existing 14 development, four reserved regression
and one historical development sheet. The 532 labels are first-pass.

The source tree was frozen before running the reserved sheets. Its Git
tree `a100cbde62da8e718a91f887d3adf9646596992d` matches the candidate on
GitHub. The Linux checks ran with outbound networking blocked. They passed
152 tests (140 non-GUI and 12 desktop), the bundled-model self-test and
the import, correction, approval, restart and export desktop self-test.
The fictional evaluator found 128 correct suggestions, zero wrong
suggestions and zero autofilled punches. The offline desktop batch imported
22 fictional photos and eight PDFs, blocked the incomplete punch and
unapproved export, and restored 30 approvals after restart. An independent
OpenPyXL read reconciled 420 dated rows, 36,670 elapsed minutes and one
overtime minute.

```sh
python -m pytest -q --ignore=tests/test_ui_safety.py
python -m pytest -q tests/test_ui_safety.py
python main.py --self-test
python main.py --gui-self-test
python experiments/evaluate_pipeline.py --manifest test_samples/ground_truth.json \
  --output "$FICTIONAL_SUMMARY"
python experiments/scan_real_forms.py --manifest "$MANIFEST" --originals "$ORIGINALS" \
  --source-sha "$CANDIDATE" --split holdout --variant original --output "$PREDICTIONS"
python experiments/evaluate_real_forms.py --manifest "$MANIFEST" --predictions "$PREDICTIONS" \
  --split holdout --output "$SUMMARY"
```

The same private commands with `--split development` produced the original,
dimmed and perspective development comparisons. The four reserved originals
were used only after selecting the policy on the development sheets.

Windows job #32 passed for the frozen source. Verification still needs the
setup executable, SHA-256 file and source manifest from that same private
job. The verified setup for a supervised fictional test is from job #31.
Lynnette's Windows acceptance and payroll owner sign-off are open.
[Windows job #32](https://circleci.com/gh/nathancspeed67401/HotelPayrollAssistant/32)
· [Build status](BUILD_STATUS.md)

## Job #31 baseline and prior OCR changes

The source tested for the verified installer was
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
