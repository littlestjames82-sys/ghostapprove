"""GhostApprove CLI.

  ghostapprove [--store DIR] ingest <request.json | ->
  ghostapprove [--store DIR] list [--status pending|approved|denied|all]
                                  [--source NAME] [--json]
  ghostapprove [--store DIR] show <id> [--json]
  ghostapprove [--store DIR] approve <id> --hash <exact-hash>
                                     [--by NAME] [--note TEXT] [--json]
  ghostapprove [--store DIR] deny <id> --hash <exact-hash>
                                  [--by NAME] [--note TEXT | --reason TEXT]
                                  [--json]
  ghostapprove [--store DIR] history [--id ID] [--json]

Exit codes: 0 success, 1 decision refused (hash mismatch, already
decided, unknown or unrecorded id), 2 invalid request / store error.

GhostApprove records decisions only. Approving a request does NOT
execute it, and nothing is ever approved automatically.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .model import RequestError, short_hash
from .store import RefusedError, Store, StoreError, default_store_path

NOT_EXECUTED = "decision recorded only - GhostApprove did NOT execute this action"


def _age_text(ingested_at) -> str:
    """Human age of a queued request, from its ingest timestamp.

    Display only: derived from the stored timestamp, never used in
    any decision logic (a request can wait forever; age approves
    nothing). Returns "unknown" when the timestamp is missing or
    unparseable rather than guessing.
    """
    if not isinstance(ingested_at, str) or not ingested_at:
        return "unknown"
    try:
        then = datetime.fromisoformat(ingested_at.replace("Z", "+00:00"))
    except ValueError:
        return "unknown"
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    seconds = int((datetime.now(timezone.utc) - then).total_seconds())
    if seconds < 0:
        return "unknown"
    if seconds < 60:
        return "just now"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h {minutes % 60}m"
    return f"{hours // 24}d {hours % 24}h"


def _store(args) -> Store:
    explicit = (getattr(args, "store_sub", None)
                or getattr(args, "queue_sub", None)
                or getattr(args, "store", None)
                or getattr(args, "queue", None))
    return Store(default_store_path(explicit))


def _print_entry_human(entry: dict) -> None:
    content = entry.get("content") or {}
    print(f"id:     {entry['id']}")
    print(f"status: {entry['status']}")
    print(f"source: {content.get('source')}")
    print(f"risk:   {content.get('risk')}")
    print(f"action: {content.get('action')}")
    print(f"summary: {content.get('summary')}")
    if content.get("requested_by"):
        print(f"requested_by: {content['requested_by']}")
    print(f"ingested_at: {entry.get('ingested_at')}")
    print(f"age:    {_age_text(entry.get('ingested_at'))}")
    print(f"hash:   {entry['hash']}")
    if content.get("diff"):
        print("diff:")
        print(content["diff"])
    if content.get("payload") is not None:
        print("payload:")
        print(json.dumps(content["payload"], indent=2, ensure_ascii=False))
    dec = entry.get("decision")
    if dec:
        print(f"decision: {dec.get('event')} by {dec.get('by')} at {dec.get('at')}")
        if dec.get("note"):
            print(f"note: {dec['note']}")


def cmd_ingest(args) -> int:
    if args.file == "-":
        text = sys.stdin.read()
    else:
        try:
            text = Path(args.file).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"error: cannot read request file: {exc}", file=sys.stderr)
            return 2
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        print(f"error: request file is not valid JSON: {exc}", file=sys.stderr)
        return 2
    try:
        entry = _store(args).ingest(raw)
    except RequestError as exc:
        print(f"error: invalid request: {exc}", file=sys.stderr)
        return 2
    except RefusedError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(entry, indent=2, ensure_ascii=False))
    else:
        print(f"ingested: {entry['id']}")
        print(f"  source: {entry['source']}  risk: {entry['risk']}")
        print(f"  action: {entry['action']}")
        print(f"  hash:   {entry['hash']}")
        print("  status: pending (recorded; nothing decided, nothing executed)")
    return 0


def cmd_list(args) -> int:
    entries = _store(args).list_requests(status=args.status, source=args.source)
    if args.json:
        slim = [{k: e[k] for k in ("id", "hash", "source", "risk", "action",
                                   "summary", "requested_by", "ingested_at",
                                   "status", "decision")} for e in entries]
        print(json.dumps(slim, indent=2, ensure_ascii=False))
        return 0
    if not entries:
        print(f"no {args.status} requests")
        return 0
    for e in entries:
        print(f"{e['id']}  [{e['status']}]  {e['source']}  risk={e['risk']}  "
              f"age={_age_text(e.get('ingested_at'))}  "
              f"hash={short_hash(e['hash'])}  {e['action']}")
    return 0


def cmd_show(args) -> int:
    entry = _store(args).get_entry(args.id)
    if args.json:
        print(json.dumps(entry, indent=2, ensure_ascii=False))
    else:
        _print_entry_human(entry)
    return 0


def _decide(args, decision: str) -> int:
    note = getattr(args, "note", None) or getattr(args, "reason", None)
    event = _store(args).decide(args.id, decision, args.hash,
                                by=args.by, note=note)
    if args.json:
        print(json.dumps(event, indent=2, ensure_ascii=False))
    else:
        print(f"{decision}: {event['id']}")
        print(f"  hash: {event['hash']}")
        print(f"  by:   {event['by']} at {event['at']}")
        if event.get("note"):
            print(f"  note: {event['note']}")
        print(f"  {NOT_EXECUTED}")
    return 0


def cmd_history(args) -> int:
    events = _store(args).history(req_id=getattr(args, "id", None))
    if args.json:
        print(json.dumps(events, indent=2, ensure_ascii=False))
        return 0
    if not events:
        print("no history")
        return 0
    for ev in events:
        extra = ""
        if ev.get("event") in ("approved", "denied"):
            extra = f" by {ev.get('by')}"
            if ev.get("note"):
                extra += f" note={ev['note']}"
        print(f"{ev.get('at')}  {ev.get('event')}  {ev.get('id')}  "
              f"hash={short_hash(ev.get('hash', ''))}{extra}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="ghostapprove",
        description="One local approval queue for the Ghost stack. "
                    "Records decisions only; executes nothing, "
                    "approves nothing automatically.")
    parser.add_argument("--version", action="version",
                        version=f"ghostapprove {__version__}")
    parser.add_argument("--store", help="store directory "
                                        "(default: $GHOSTAPPROVE_DIR or ./.ghostapprove)")
    parser.add_argument("--queue", help="alias for --store (queue directory)")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--store", dest="store_sub", default=None,
                        help="store directory (same as the global --store)")
    common.add_argument("--queue", dest="queue_sub", default=None,
                        help="alias for --store (queue directory)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("ingest", parents=[common], help="ingest a local JSON request file into the queue")
    p.add_argument("file", help="request JSON file, or - for stdin")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_ingest)

    p = sub.add_parser("list", parents=[common], help="list queued requests (default: pending, oldest first)")
    p.add_argument("--status", default="pending",
                   choices=["pending", "approved", "denied", "all"])
    p.add_argument("--source")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("show", parents=[common], help="show one request in full: summary, diff, risk, exact hash")
    p.add_argument("id")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_show)

    for name, helptext in (("approve", "record an approval against the exact hash"),
                           ("deny", "record a denial against the exact hash")):
        p = sub.add_parser(name, parents=[common], help=helptext)
        p.add_argument("id")
        p.add_argument("--hash", required=True,
                       help="REQUIRED: the exact hash shown for this request")
        p.add_argument("--by", default="local-operator",
                       help="decider label (recorded, not authenticated)")
        p.add_argument("--note")
        if name == "deny":
            p.add_argument("--reason", help="alias for --note on deny")
        p.add_argument("--json", action="store_true")
        p.set_defaults(func=lambda a, d=name + "d" if name == "approve" else "denied": _decide(a, d))

    p = sub.add_parser("history", parents=[common], help="show the append-only ledger in order")
    p.add_argument("--id", help="only events for this request id")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=cmd_history)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except RefusedError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    except (StoreError, RequestError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
