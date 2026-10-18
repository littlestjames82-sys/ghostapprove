"""GhostApprove: one local approval queue for the Ghost stack.

Zero-dependency Python stdlib only. Local only, no network.
GhostApprove is a queue and a recorder only: it never executes an
approved action and never approves anything on its own. A decision
exists only when a human runs approve/deny with the exact hash that
was shown for a recorded request.
"""

__version__ = "0.1.0"
