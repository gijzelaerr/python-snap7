"""Hand-written orchestrator for Family-0 Monolith9.

The C# source delegates to 11 Part subprograms that share a common
``locals`` scratch array. We mirror that structure here. The Parts
themselves are mechanically transpiled — see ``s7/session_auth/family0/nine/``.
"""

from __future__ import annotations

from .nine import (
    part1,
    part2,
    part3,
    part4,
    part5,
    part6,
    part7,
    part8,
    part9,
    part10,
    part11,
)


def execute(destination: bytearray, source: bytes) -> None:
    """Run Monolith9 by chaining its 11 Part subprograms."""
    locals_: list[int] = [0] * 831
    part1.execute(source, locals_)
    part2.execute(source, locals_)
    part3.execute(locals_)
    part4.execute(locals_)
    part5.execute(locals_)
    part6.execute(locals_)
    part7.execute(locals_)
    part8.execute(locals_)
    part9.execute(locals_)
    part10.execute(locals_)
    part11.execute(destination, locals_)
