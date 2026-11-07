# Windows build status · November 7, 2026

**Engineering candidate. Setup verification and Lynnette's PC acceptance are open.**

| Windows Server 2022 job | Exact source | Status |
| --- | --- | --- |
| [CircleCI #31](https://circleci.com/gh/nathancspeed67401/HotelPayrollAssistant/31) | [`cbe6022463429fa6b42bd94613bb77ba0a448b0c`](https://github.com/nathancspeed67401/HotelPayrollAssistant/commit/cbe6022463429fa6b42bd94613bb77ba0a448b0c) | Passed |
| [CircleCI #30](https://circleci.com/gh/nathancspeed67401/HotelPayrollAssistant/30) | `fe4c8486f84a431884a76cb4ef961e43828ff14a` | Failed. First failing step requires its signed-in log. |
| [CircleCI #29](https://circleci.com/gh/nathancspeed67401/HotelPayrollAssistant/29) | `fbeb143768d359fb543aa0ca366fff35077e6d7b` | Passed on earlier source |
| [CircleCI #28](https://circleci.com/gh/nathancspeed67401/HotelPayrollAssistant/28) | `9a46c916334d56e9460a3939a2b7a497caf445d0` | Passed on main |

The Windows workflow verifies the bundled OCR model, isolates the test
executables from outbound traffic, runs pytest, builds the Inno Setup package,
and checks installed offline import, review, export, restart and uninstall.
GitHub's exact-commit status reports success for job #31.

## Verify the private installer

Open the signed-in **Artifacts** tab for job #31 and obtain these files
from the same job.

- `Windows-Setup/HotelPayrollAssistant_Setup.exe`
- `Verification/installer-sha256.txt`
- `Verification/source-commit.txt`

The artifact API returned HTTP 404 without signed-in project access. The
installer bytes, their SHA-256 and the source manifest have yet to be
checked. Compare the SHA-256 of the downloaded executable with the checksum
file and verify that the source manifest contains the exact #31 commit above.
Then use the fictional acceptance pack and [Windows checklist](RELEASE_STATUS.md)
on Lynnette's PC.
