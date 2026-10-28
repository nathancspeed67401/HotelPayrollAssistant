# Build status — October 28, 2026

Windows build provider: CircleCI. GitHub Actions is intentionally not included.

The source was recovered from the saved v0.3 research ZIP after workspace cleanup.
The correction autosave, approval invalidation, strict fourteen-row review checks,
split-shift overlap detection and same-batch duplicate filtering were restored.
The bundled SVC model was trained with scikit-learn 1.8.0; that version is pinned.

Current local verification: 39 tests passed, 3 desktop tests skipped because this
Linux session has no display. The application dependency/export self-test passed.
CircleCI runs those desktop tests on Windows, creates an Inno Setup installer,
silently installs it, exercises the installed OCR/model/calculation/export path,
and opens and closes the installed GUI. Verification artifacts record the commit,
dependency versions and installer SHA-256.

The CircleCI project must be connected to this repository and its workflow must
finish successfully before an installer can be described as tested. No successful
Windows build has been verified yet.

Release remains blocked by handwriting accuracy. The shipped recognizer is the
experimental v0.3 model. Its historical composite benchmark was 34/66 exact time
entries; the saved report documents that the original employee form yielded no
usable punches. Later TrOCR/RapidOCR experiments were not saved in the recovery
ZIP and are not part of this build. Every day must still be reviewed manually.

Do not distribute this engineering build as a completed payroll release.
