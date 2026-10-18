# GhostApprove

**One local inbox for every "can I do this?" your agents ask, with the decision written down against an exact fingerprint.**

Agent Seatbelt asks before a consequential agent action. GhostGuard asks at its policy gate. GhostDeploy asks before a governed deploy. Ghost Bridge carries tasks that need a human yes or no. Until now each of those kept its own record, in its own shape, or no durable record at all.

GhostApprove is the shared queue in front of all of them. A tool writes a small JSON request file. You run one command to put it in the queue, read it in one plain format (what, why, how risky, identified by an exact hash), and record approve or deny against that hash. Later, anyone can audit exactly what was asked and what was decided, from two plain files on disk.

By Ghost Developer Studio. GhostApprove is the approval companion in the GhostSlice family.

## The one rule that matters

**GhostApprove records decisions. It never carries them out.**

Approving a request here does not run it, deploy it, send it, or change anything outside the GhostApprove store. The tool that asked reads the decision record and decides for itself what to do. There is no executor in this version, on purpose: an approval queue that quietly becomes an execution pipeline is exactly the failure this tool exists to prevent.

And nothing is ever approved automatically. No timeout, no risk rule, no `--yes`, no `--all`, no config or environment variable approves anything. A request stays pending until a human runs an approve or deny command naming its exact hash.

## What you need

Python 3.10 or newer. No accounts, no network, no dependencies.

## The everyday commands

From the GhostApprove folder, with an optional store folder (default `.ghostapprove/` in the current directory, or `$GHOSTAPPROVE_DIR`):

```bash
# 1. Put a request in the queue
PYTHONPATH=src python3 -m ghostapprove --store .ghostapprove ingest examples/ghostbridge-request.json

# 2. See what is waiting (oldest first)
PYTHONPATH=src python3 -m ghostapprove --store .ghostapprove list

# 3. Read one request in full, including its exact hash
PYTHONPATH=src python3 -m ghostapprove --store .ghostapprove show req-ghostbridge-001

# 4. Decide, naming the exact hash you just read
PYTHONPATH=src python3 -m ghostapprove --store .ghostapprove approve req-ghostbridge-001 --hash <exact-hash-from-show> --by ryan
PYTHONPATH=src python3 -m ghostapprove --store .ghostapprove deny    req-ghostdeploy-001 --hash <exact-hash-from-show> --note "not yet"

# 5. Audit everything that happened, in order
PYTHONPATH=src python3 -m ghostapprove --store .ghostapprove history
```

Every command also accepts `--json`. `list` accepts `--status pending|approved|denied|all` and `--source <name>`. `history` accepts `--id <id>`. Human `list` rows and the `show` view also display how long a request has been waiting (age, display only; it never affects a decision).

Exit codes: 0 success, 1 decision refused (hash mismatch, already decided, unknown id), 2 invalid request or store error.

## Why the hash is required

The hash is a sha256 fingerprint of the exact request content, computed when the request enters the queue and shown everywhere the request appears. A decision is only recorded if all of these match at decision time:

1. The hash you supply equals the hash on record.
2. The hash recomputed from the stored record still equals the hash on record, so a record edited after you reviewed it cannot be approved as if it were the request you saw.
3. The `ingested` ledger event for that id carries that same hash, so a record file swapped wholesale for a different request cannot be approved under this id.
4. The request is still pending, so it can never be decided twice.

If any check fails, the decision is refused and **nothing is written**. A recorded approval is evidence that a human saw a specific hash and decided. It is not proof that the originating tool acted, or acted correctly, and GhostApprove's own output says "decision recorded" for exactly that reason.

## The request file

One JSON file per request. Required: `action` (what is being asked) and `summary` (why, in plain words). Also recognised:

| Field | Meaning |
|---|---|
| `source` | Who is asking: `seatbelt`, `ghostguard`, `ghostdeploy`, `ghostbridge`, `manual`, or any short producer name |
| `risk` | `low`, `medium`, `high`, or `critical`. Defaults to `medium`. Any other value is refused, not guessed |
| `diff` | Optional change summary or unified diff text, shown verbatim |
| `payload` | Optional JSON describing the exact action the producer would take |
| `requested_by` | Optional label for who or what raised the request |
| `id` | Optional. Must be unique; re-using an existing id is refused. Generated from the content hash when omitted |

Producers: **never put a raw secret value in a request.** Name a secret by reference only. The store is a local file, but treat it as sensitive anyway, and keep it out of git.

Four ready-made requests are in `examples/` (one per source), with a worked run in `examples/WALKTHROUGH.md`.

## The store

```
.ghostapprove/
  requests/<id>.json   one record per request, never edited after ingest
  ledger.jsonl         append-only events: ingested, approved, denied
```

A decision is an appended ledger line, never an edit to the record, and there is no delete, clear, or undo command. Refused decision attempts are shown to the operator and are not written to the ledger: the ledger records facts, not attempts. Any status you see can be reproduced from these two files alone.

Writes are crash-conscious: a record is fsynced and atomically renamed into place before its ledger event is appended, ledger appends are fsynced, and a new event is never merged onto a torn (partial) final ledger line. Damage fails closed: if the ledger or a record cannot be read back exactly, ingest and decisions refuse with an error and write nothing until an operator repairs the file. Nothing is ever silently skipped, repaired by guessing, or decided around.

## What GhostApprove does not do

- It does not execute, dispatch, deploy, or send anything. Ever, in this version.
- It does not approve anything automatically, and low risk is a display label only.
- It does not talk to Seatbelt, Guard, Deploy, or Bridge. No polling, no webhooks, no server, no network at all. A producer writes a file; a human ingests it.
- It does not authenticate the human. `--by` is a recorded label on a single-operator local store, not an identity proof.
- It does not edit or delete requests or decisions.

## Pricing

Not decided, not public. The core follows the house MIT pattern; no pricing or release has been set for GhostApprove.
