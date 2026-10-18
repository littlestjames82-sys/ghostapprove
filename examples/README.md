# Examples

Four sample approval requests, one per GhostApprove source. All data is
fictional and safe: no real secrets, no real targets.

| File | Source | Risk | What is being asked |
|---|---|---|---|
| `seatbelt-request.json` | seatbelt | high | Run a cleanup script outside the project folder. Its payload names a side-effect file (`examples/SHOULD_NOT_EXIST_seatbelt.txt`) that the test suite uses to prove approving never executes anything: that file must never appear. |
| `ghostguard-request.json` | ghostguard | medium | Read one setting name from a config file that matched a secrets pattern (values are never in the request). |
| `ghostdeploy-request.json` | ghostdeploy | high | Deploy a release to an internal staging unit, with a diff summary. |
| `ghostbridge-request.json` | ghostbridge | low | Post a short status note to a shared board. |

See `WALKTHROUGH.md` for a full ingest, decide, and audit run using
two of these files.
