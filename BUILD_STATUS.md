# Windows build status · November 7, 2026

**v0.5.2 engineering candidate. Use fictional timesheets for acceptance.**

| Windows Server 2022 job | Exact source | Status |
| --- | --- | --- |
| [CircleCI #27](https://circleci.com/gh/nathancspeed67401/HotelPayrollAssistant/27) | [`a9b641417350c621858ef07ab748a28d38df7ac0`](https://github.com/nathancspeed67401/HotelPayrollAssistant/commit/a9b641417350c621858ef07ab748a28d38df7ac0) | Passed |
| [CircleCI #26](https://circleci.com/gh/nathancspeed67401/HotelPayrollAssistant/26) | [`bb467ffb7cbe951899823bbf535a2ca2f70b99bd`](https://github.com/nathancspeed67401/HotelPayrollAssistant/commit/bb467ffb7cbe951899823bbf535a2ca2f70b99bd) | Passed |
| [CircleCI #25](https://circleci.com/gh/nathancspeed67401/HotelPayrollAssistant/25) | `21e666954f43eef2b340235f6d1bf384d0529910` | Passed |

The job compiles the Inno Setup executable, installs it, exercises real offline
recognition and the desktop workflow with fictional photo and PDF inputs,
and uninstalls it. The candidate passed 122 local tests with external
network access blocked and the display set to 1366×768.

Open the candidate job's **Artifacts** tab with an authenticated CircleCI
account that can access this payroll project. The configured installer is
`Windows-Setup/HotelPayrollAssistant_Setup.exe`. The corresponding checksum and
commit manifests are under `Verification`.

The session could verify the job status through GitHub. The private artifact
listing was inaccessible, so the setup bytes and SHA-256 are unverified
independently. Windows 10/11 field testing and Lynnette's acceptance remain open.

See [Release status](RELEASE_STATUS.md) for the test workflow and
[Development progress](DEVELOPMENT_PROGRESS.md) for the remaining gates.
