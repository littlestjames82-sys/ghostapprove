"""Request normalisation and exact-hash computation for GhostApprove.

Canonical content is the normalised request dict WITHOUT the id,
ingest timestamp, or hash. The exact hash is sha256 over the canonical
JSON serialisation (sorted keys, compact separators, UTF-8), so the
same content always produces the same hash and any edit to a stored
record changes the recomputed hash.
"""
from __future__ import annotations

import hashlib
import json
import re

RISKS = ("low", "medium", "high", "critical")
DEFAULT_RISK = "medium"
DEFAULT_SOURCE = "manual"

# Fields that make up canonical content, in the normalised record.
CONTENT_FIELDS = ("source", "action", "summary", "risk", "diff",
                  "payload", "requested_by")

_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class RequestError(ValueError):
    """Raised when a request file is invalid; CLI maps it to exit 2."""


def canonical_json(content: dict) -> str:
    return json.dumps(content, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def content_hash(content: dict) -> str:
    return hashlib.sha256(canonical_json(content).encode("utf-8")).hexdigest()


def short_hash(full_hash) -> str:
    """First 12 hex chars for display; tolerant of a missing or
    non-string hash in a hand-damaged ledger line (renders empty
    rather than crashing the history view)."""
    if not isinstance(full_hash, str):
        return ""
    return full_hash[:12]


def validate_id(raw) -> str:
    if not isinstance(raw, str) or not _ID_RE.match(raw):
        raise RequestError(
            "id must be a string of letters, digits, '.', '_' or '-', "
            "starting with a letter or digit, max 128 chars")
    if raw in (".", "..") or ".." in raw.split("."):
        raise RequestError("id must not contain path traversal")
    return raw


def normalise_request(raw) -> tuple[dict, str | None]:
    """Validate and normalise a parsed JSON request.

    Returns (canonical_content, requested_id_or_None).
    Raises RequestError on any invalid field.
    """
    if not isinstance(raw, dict):
        raise RequestError("request must be a JSON object")

    action = raw.get("action")
    if not isinstance(action, str) or not action.strip():
        # 'title' is an accepted producer fallback for action.
        action = raw.get("title")
    if not isinstance(action, str) or not action.strip():
        raise RequestError("request requires a non-empty string 'action'")

    summary = raw.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        # 'description' is an accepted producer fallback for summary.
        summary = raw.get("description")
    if not isinstance(summary, str) or not summary.strip():
        raise RequestError("request requires a non-empty string 'summary'")

    source = raw.get("source", DEFAULT_SOURCE)
    if not isinstance(source, str) or not source.strip():
        raise RequestError("'source' must be a non-empty string")
    source = source.strip()

    risk = raw.get("risk", DEFAULT_RISK)
    if not isinstance(risk, str) or risk.strip().lower() not in RISKS:
        raise RequestError(
            f"'risk' must be one of {', '.join(RISKS)} (got {risk!r}); "
            "refusing rather than guessing")
    risk = risk.strip().lower()

    diff = raw.get("diff")
    if diff is not None and not isinstance(diff, str):
        raise RequestError("'diff' must be a string when present")

    requested_by = raw.get("requested_by")
    if requested_by is not None and not isinstance(requested_by, str):
        raise RequestError("'requested_by' must be a string when present")

    payload = raw.get("payload")  # any JSON value, may be absent/None

    content = {
        "source": source,
        "action": action.strip(),
        "summary": summary.strip(),
        "risk": risk,
        "diff": diff,
        "payload": payload,
        "requested_by": requested_by,
    }
    req_id = raw.get("id")
    if req_id is not None:
        req_id = validate_id(req_id)
    return content, req_id
