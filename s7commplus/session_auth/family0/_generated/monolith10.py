"""Hand-written orchestrator for Family-0 Monolith10.

Mirrors the C# source which delegates to 3 Part subprograms sharing
a 301-element ``locals`` scratch array. The Parts themselves are
mechanically transpiled — see ``s7/session_auth/family0/ten/``.
"""

from __future__ import annotations

from .ten import part1, part2, part3


def execute(destination: bytearray, source: bytes) -> None:
    """Run Monolith10 by chaining its 3 Part subprograms."""
    locals_: list[int] = [0] * 301
    part1.execute(source, locals_)
    part2.execute(locals_)
    part3.execute(destination, locals_)
