# Windows build status · November 7, 2026

**Verified engineering installer for supervised testing with fictional data. Lynnette's PC acceptance is open.**

| Windows Server 2022 job | Exact source | Status |
| --- | --- | --- |
| [CircleCI #31](https://circleci.com/gh/nathancspeed67401/HotelPayrollAssistant/31) | [`cbe6022463429fa6b42bd94613bb77ba0a448b0c`](https://github.com/nathancspeed67401/HotelPayrollAssistant/commit/cbe6022463429fa6b42bd94613bb77ba0a448b0c) | Passed |
| [CircleCI #30](https://circleci.com/gh/nathancspeed67401/HotelPayrollAssistant/30) | `fe4c8486f84a431884a76cb4ef961e43828ff14a` | Failed. CircleCI shows one failed test, `test_partial_pay_period_date_is_not_copied_to_other_employees`. The assertion details require its signed-in log. |
| [CircleCI #29](https://circleci.com/gh/nathancspeed67401/HotelPayrollAssistant/29) | `fbeb143768d359fb543aa0ca366fff35077e6d7b` | Passed on earlier source |
| [CircleCI #28](https://circleci.com/gh/nathancspeed67401/HotelPayrollAssistant/28) | `9a46c916334d56e9460a3939a2b7a497caf445d0` | Passed on main |

The Windows workflow verifies the bundled OCR model, isolates the test
executables from outbound traffic, runs pytest, builds the Inno Setup package,
and checks installed offline import, review, export, restart and uninstall.
GitHub's exact-commit status reports success for job #31.

## Verified installer

The uploaded `HotelPayrollAssistant_Setup.exe` is a 204,455,302 byte Windows
Inno Setup package. Its SHA-256 was computed directly from the uploaded
bytes and matched the value supplied from job #31's
`Verification/installer-sha256.txt`.

`9cda000edf5c7f269967257bc00d0569f3bfbb35b1b19b04118494af5dda0cba`

The copied `Verification/source-commit.txt` value was
`cbe6022463429fa6b42bd94613bb77ba0a448b0c`, matching the GitHub status
for passing job #31. The PE certificate table is empty, so the test
installer carries no embedded Authenticode signature.

The installer is ready for a supervised Windows test with the fictional
acceptance pack. Follow the [Windows checklist](RELEASE_STATUS.md) and
record Lynnette's PC results.
