# Walkthrough

A complete GhostApprove run: two requests in, one approval, one denial,
one refused double decision, and the audit trail. Every command below
was run verbatim by Agent B on Oct 14, 2026 against Agent A's core,
from `~/workspace/ghostapprove`, with a throwaway store at
`/tmp/ga-walk`. The hashes are content hashes, so re-running this on
the unchanged example files reproduces the same hashes.

```bash
export PYTHONPATH=src

# 1. Ingest two requests
python3 -m ghostapprove --store /tmp/ga-walk ingest examples/ghostbridge-request.json
# ingested: req-ghostbridge-001
#   source: ghostbridge  risk: low
#   hash:   add7e122a394fe3eb2969fbeab5d1ec83a776d63aaed275b54abcd8c331c7ca7
#   status: pending (recorded; nothing decided, nothing executed)

python3 -m ghostapprove --store /tmp/ga-walk ingest examples/ghostdeploy-request.json
# ingested: req-ghostdeploy-001
#   source: ghostdeploy  risk: high
#   hash:   fd7f7d7129903f4c244355991e44d15a9f8f892bfbaeca946d681f9e35170496

# 2. The queue, oldest first, short hashes on the list view
python3 -m ghostapprove --store /tmp/ga-walk list
# req-ghostbridge-001  [pending]  ghostbridge  risk=low   hash=add7e122a394  Post a short build-status note ...
# req-ghostdeploy-001  [pending]  ghostdeploy  risk=high  hash=fd7f7d712990  Deploy release 2026.10.14-1 ...

# 3. Show one request in full before deciding (full hash, summary, payload)
python3 -m ghostapprove --store /tmp/ga-walk show req-ghostbridge-001

# 4. Decide, naming the exact hash from show
python3 -m ghostapprove --store /tmp/ga-walk approve req-ghostbridge-001 \
  --hash add7e122a394fe3eb2969fbeab5d1ec83a776d63aaed275b54abcd8c331c7ca7 \
  --by ryan --note "ok to post"
# approved: req-ghostbridge-001
#   decision recorded only - GhostApprove did NOT execute this action

python3 -m ghostapprove --store /tmp/ga-walk deny req-ghostdeploy-001 \
  --hash fd7f7d7129903f4c244355991e44d15a9f8f892bfbaeca946d681f9e35170496 \
  --by ryan --note "not yet"
# denied: req-ghostdeploy-001
#   decision recorded only - GhostApprove did NOT execute this action

# 5. A second decision on a decided request is refused (exit 1, nothing written)
python3 -m ghostapprove --store /tmp/ga-walk approve req-ghostbridge-001 \
  --hash add7e122a394fe3eb2969fbeab5d1ec83a776d63aaed275b54abcd8c331c7ca7 --by ryan
# refused: request req-ghostbridge-001 is already approved; a second decision is refused, nothing recorded

# 6. Audit: the append-only history, in order
python3 -m ghostapprove --store /tmp/ga-walk history
# ... ingested  req-ghostbridge-001  hash=add7e122a394
# ... ingested  req-ghostdeploy-001  hash=fd7f7d712990
# ... approved  req-ghostbridge-001  hash=add7e122a394 by ryan note=ok to post
# ... denied    req-ghostdeploy-001  hash=fd7f7d712990 by ryan note=not yet
```

What to notice:

- Approving the bridge note did not post anything. Denying the deploy
  did not touch staging. GhostApprove only wrote two ledger lines.
- The store afterwards is exactly two record files plus the ledger:
  `/tmp/ga-walk/requests/req-ghostbridge-001.json`,
  `/tmp/ga-walk/requests/req-ghostdeploy-001.json`, and
  `/tmp/ga-walk/ledger.jsonl`. The record files are byte-identical
  before and after the decisions; decisions live only in the ledger.
- Try approving with one hex digit of the hash changed: refused, exit
  1, and the ledger does not grow. The test suite covers that, the
  stored-record tamper case, and the deny path in
  `tests/test_decisions.py`.
