#!/usr/bin/env python3
"""Mechanical C# → Python transpiler for HarpoS7 Family-0 monolith files.

Each Monolith*.cs in HarpoS7.Family0/Monoliths is a straight-line
transform from a source byte buffer to a destination byte buffer,
implemented as a forest of bitwise expressions on 32-bit unsigned
locals. There is no internal control flow inside ``Execute`` (only
buffer-length guards at the top), and every statement is one of:

  - ``uint uVarN;`` (declaration — discard, Python doesn't need it)
  - ``uVarN = <expr>;`` or ``dstDwords[idx] = <expr>;`` (assignment)
  - ``return <ident>;`` (return)

The transpiler treats the body as a stream of `;`-terminated
statements, rewrites each statement with the substitutions listed in
``_SUBS``, masks unbounded Python ints back to uint32 on assignment,
and emits a single Python function. The result passes the same vector
test the C# original ships in ``HarpoS7.Family0.Tests``.

Usage::

    python tools/transpile_harpo_monolith.py \\
        --source /path/to/HarpoS7.Family0/Monoliths/Monolith1.cs \\
        --output s7/session_auth/family0/monolith1.py

Limitations the MVP does NOT handle (none observed in HarpoS7's
Family-0/Monoliths/*.cs as of revision shipped with HarpoS7 1.1.0):

  - Branches / loops inside Execute (the wrapper ``Loop`` is special-cased)
  - String literals
  - Array literal initializers
  - Multi-dimensional indexing
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

# ---------------------------------------------------------------------------
# Lexical substitutions — applied to each statement after stripping `;`
#
# Order matters: longer keys first to avoid partial overlaps.
_SUBS: tuple[tuple[str, str], ...] = (
    # Different monoliths use different aliases for the
    # MemoryMarshal.Cast<byte, uint>(source) / (destination) views.
    # Normalise them all to a single canonical name. The trailing `[`
    # disambiguates from `source.Length` etc.
    (re.escape("dstDwords["), "dst_dwords["),
    (re.escape("srcDwords["), "src_dwords["),
    (r"\bdst\[", "dst_dwords["),
    (r"\bsrc\[", "src_dwords["),
    # `locals` is a Python builtin; rename to a safe alias.
    (r"\blocals\[", "locals_["),
    # Hex literals with a `U` suffix — Python doesn't accept the suffix.
    (r"\b(0[xX][0-9A-Fa-f]+)U\b", r"\1"),
    # Left-shift in C# uint truncates to 32 bits; Python int doesn't.
    (r"(\))\s*<<\s*(0x[0-9a-fA-F]+|\d+)", r"\1 << \2 & 0xFFFFFFFF"),
    (r"(\w+(?:\[\w+\])?)\s*<<\s*(0x[0-9a-fA-F]+|\d+)", r"(\1 << \2 & 0xFFFFFFFF)"),
    # Same for `* 2` — uint multiplication also truncates.
    (r"(\))\s*\*\s*2\b", r"\1 * 2 & 0xFFFFFFFF"),
    (r"(\w+(?:\[\w+\])?)\s*\*\s*2\b", r"(\1 * 2 & 0xFFFFFFFF)"),
    # Right-shift on identifiers: `ident >> N` → `_shr(ident, N)`.
    # The `) >> N` case is handled by _fix_right_shifts (needs paren
    # matching). The `ident >> N` case is simpler and caught here.
    (r"(\w+(?:\[\w+\])?)\s*>>\s*(0x[0-9a-fA-F]+|\d+)", r"_shr(\1, \2)"),
)


@dataclass(frozen=True)
class Signature:
    """Decoded ``Execute`` parameters.

    All fields are `True` when the parameter appears in the C# signature.
    The Family-0 transforms only ever pass ``source`` and ``destination``
    as ``Span<byte>`` / ``ReadOnlySpan<byte>`` and ``locals`` as
    ``Span<uint>``.
    """

    has_source: bool
    has_destination: bool
    has_locals: bool
    return_type: str  # "uint" or "void"


@dataclass
class TranspiledMonolith:
    """The Python source for one monolith, ready to write."""

    name: str  # e.g. "Monolith1"
    body_lines: list[str]
    return_var: str  # e.g. "uVar99" or "" if void
    signature: Signature


def _strip_comments(text: str) -> str:
    """Remove `//` line comments and `/* ... */` block comments."""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"//[^\n]*", "", text)
    return text


def _extract_execute(source: str, monolith_class: str) -> tuple[str, str, Signature]:
    """Return ``(body_text, return_var_name, signature)`` for ``Execute``.

    ``body_text`` is the raw C# inside ``Execute``'s outer braces, with
    all comments stripped; ``return_var`` is the identifier returned
    (e.g. "uVar99"), or "" when the method is ``void``; ``signature``
    encodes which parameters the method takes.
    """
    text = _strip_comments(source)

    # Match `public static [type] Execute(args) { ... }`
    sig_match = re.search(
        r"public\s+static\s+(uint|void)\s+Execute\s*\(",
        text,
    )
    if sig_match is None:
        raise ValueError(f"no Execute method found in {monolith_class}")
    return_type = sig_match.group(1)

    # Capture the parameter list between the parens.
    open_paren = text.index("(", sig_match.end() - 1)
    paren_depth = 0
    i = open_paren
    params_start = open_paren + 1
    while i < len(text):
        c = text[i]
        if c == "(":
            paren_depth += 1
        elif c == ")":
            paren_depth -= 1
            if paren_depth == 0:
                params_text = text[params_start:i]
                i += 1
                break
        i += 1
    else:
        raise ValueError(f"unterminated parameter list in {monolith_class}.Execute")

    sig_obj = Signature(
        has_source="source" in params_text,
        has_destination="destination" in params_text,
        has_locals="locals" in params_text,
        return_type=return_type,
    )

    # Find the opening brace of the method body.
    while i < len(text) and text[i] != "{":
        i += 1
    if i >= len(text):
        raise ValueError(f"no opening brace for Execute in {monolith_class}")
    body_start = i + 1

    # Match the closing brace, tracking nesting.
    brace_depth = 1
    j = body_start
    while j < len(text) and brace_depth > 0:
        c = text[j]
        if c == "{":
            brace_depth += 1
        elif c == "}":
            brace_depth -= 1
        j += 1
    if brace_depth != 0:
        raise ValueError(f"unbalanced braces in {monolith_class}.Execute")
    body = text[body_start : j - 1]

    # Find the return statement (only present when uint return).
    return_var = ""
    if return_type == "uint":
        m = re.search(r"\breturn\s+(\w+)\s*;", body)
        if m is None:
            raise ValueError(f"no return in uint Execute of {monolith_class}")
        return_var = m.group(1)

    return body, return_var, sig_obj


def _split_statements(body: str) -> list[str]:
    """Split a body into `;`-terminated statements, preserving order.

    Whitespace and newlines inside a statement are collapsed; the
    output statements are single-line for ease of post-processing.
    """
    # Collapse whitespace runs.
    flat = re.sub(r"\s+", " ", body).strip()
    parts = [p.strip() for p in flat.split(";")]
    return [p for p in parts if p]


def _statement_to_python(stmt: str) -> str | None:
    """Translate one C# statement to a Python line.

    Returns ``None`` if the statement is uninteresting (a type
    declaration or a guard we want to discard).
    """
    # Type-only declarations: `uint uVar1` (no `=`).
    if re.fullmatch(r"uint\s+\w+", stmt):
        return None

    # Discard the buffer-size guards — we re-emit them in the wrapper.
    if "BufferLengthException" in stmt:
        return None
    if stmt.startswith("if "):
        return None  # `if (source.Length < ...) throw ...` (no body, single-stmt)
    if stmt.startswith("throw "):
        return None

    # Apply lexical substitutions.
    rewritten = stmt
    for needle, replacement in _SUBS:
        rewritten = re.sub(needle, replacement, rewritten)

    # The cast lines bind src_dwords / dst_dwords; we replace them
    # with our own helper calls in the emitted preamble, so drop these.
    if "MemoryMarshal.Cast" in rewritten:
        return None

    # Strip `uint` from declarations that include an initializer:
    # `uint uVar1 = expr` → `uVar1 = expr`.
    rewritten = re.sub(r"^uint\s+", "", rewritten).strip()

    # Replace `) >> N` with `_shr(`, N) — wrapping the parenthesized
    # subexpression in a _shr call that masks to uint32 before shifting.
    # This fixes ~X ^ Y >> N where Python's arithmetic shift sign-extends
    # but C#'s uint logical shift zero-fills.
    rewritten = _fix_right_shifts(rewritten)

    # Mask uint32 on every assignment to an ident or dst_dwords[N].
    # The return statement is re-emitted by the wrapper, after the
    # final dst_dwords flush. Drop it from the body.
    if rewritten.startswith("return "):
        return None

    if "=" in rewritten and not rewritten.startswith("return"):
        lhs, _, rhs = rewritten.partition("=")
        return f"{lhs.strip()} = ({rhs.strip()}) & 0xFFFFFFFF"

    return rewritten


def _fix_right_shifts(stmt: str) -> str:
    """Replace `(expr) >> N` with `_shr(expr, N)`.

    Finds each `) >> literal` pattern, walks backward to find the
    matching `(`, and wraps the content in `_shr(content, N)`.
    """
    result = stmt
    while True:
        m = re.search(r"\)\s*>>\s*(0x[0-9a-fA-F]+|\d+)", result)
        if not m:
            break
        shift_amount = m.group(1)
        close_paren_pos = m.start()

        # Find matching open paren
        depth = 0
        i = close_paren_pos
        while i >= 0:
            if result[i] == ")":
                depth += 1
            elif result[i] == "(":
                depth -= 1
                if depth == 0:
                    break
            i -= 1

        if i < 0 or depth != 0:
            # Can't find matching paren — skip this occurrence
            # (replace >> with a marker to avoid infinite loop)
            result = result[: m.start()] + ") __SHR__ " + shift_amount + result[m.end() :]
            continue

        # Check if there's a `~` immediately before the `(` — if so,
        # include it as part of the operand (C#'s `~(X) >> N` means
        # "shift the NOT of X", not "NOT of shift of X").
        prefix_start = i
        while prefix_start > 0 and result[prefix_start - 1] == "~":
            prefix_start -= 1

        # Extract the full expression including any leading ~
        inner = result[prefix_start : close_paren_pos + 1]  # includes parens and ~
        # Build replacement: _shr(inner, N)
        replacement = f"_shr({inner}, {shift_amount})"
        result = result[:prefix_start] + replacement + result[m.end() :]

    # Restore any __SHR__ markers (shouldn't happen in practice)
    result = result.replace("__SHR__", ">>")
    return result


def transpile_monolith(source: str, monolith_class: str) -> TranspiledMonolith:
    body, return_var, signature = _extract_execute(source, monolith_class)
    statements = _split_statements(body)
    py_lines = []
    for stmt in statements:
        translated = _statement_to_python(stmt)
        if translated is not None:
            py_lines.append(translated)

    return TranspiledMonolith(
        name=monolith_class,
        body_lines=py_lines,
        return_var=return_var,
        signature=signature,
    )


_PREAMBLE = """\
\"\"\"Auto-generated from {source_path}.

DO NOT EDIT — regenerate via tools/transpile_harpo_monolith.py.

Mechanically transpiled from HarpoS7's Family-0 ``{class_name}.Execute``.
Vector-verified against ``HarpoS7.Family0.Tests/Blobs/Monoliths/``.
\"\"\"

from __future__ import annotations

import struct

_U32 = 0xFFFFFFFF


def _shr(x: int, n: int) -> int:
    \"\"\"Logical right-shift (mask to uint32 before shifting).

    Python's ``>>`` on negative ints does arithmetic shift (sign-extends).
    C#'s ``uint >> n`` does logical shift (zero-fills). This helper
    ensures Python behaves identically to C#.
    \"\"\"
    return (x & _U32) >> n


def _to_uints(buf: bytes | bytearray) -> list[int]:
    n = len(buf) // 4
    return list(struct.unpack(f\"<{{n}}I\", bytes(buf[: n * 4])))


def _from_uints(uints: list[int]) -> bytes:
    return struct.pack(f\"<{{len(uints)}}I\", *(u & _U32 for u in uints))
"""


def emit_python(t: TranspiledMonolith, source_path: str) -> str:
    """Return the Python source for the transpiled monolith."""

    s = t.signature
    out: list[str] = []
    out.append(_PREAMBLE.format(source_path=source_path, class_name=t.name))
    out.append("")

    # C# signature parameter order: destination, source, locals.
    params: list[str] = []
    if s.has_destination:
        params.append("destination: bytearray")
    if s.has_source:
        params.append("source: bytes")
    if s.has_locals:
        params.append("locals_: list[int]")
    return_annotation = " -> int" if t.return_var else " -> None"
    out.append(f"def execute({', '.join(params)}){return_annotation}:")
    out.append('    """Run the transpiled body."""')

    if s.has_source:
        out.append("    src_dwords = _to_uints(source)")
    if s.has_destination:
        out.append("    dst_dwords = _to_uints(destination)")
    out.append("")

    for line in t.body_lines:
        out.append(f"    {line}")
    out.append("")

    if s.has_destination:
        out.append("    destination[: len(dst_dwords) * 4] = _from_uints(dst_dwords)")
    if t.return_var:
        out.append(f"    return {t.return_var} & _U32")
    out.append("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument(
        "--source",
        required=True,
        type=Path,
        help="Path to MonolithN.cs",
    )
    p.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Path to write the transpiled Python file",
    )
    p.add_argument(
        "--class-name",
        default=None,
        help="C# class name (default: derive from --source filename)",
    )
    args = p.parse_args(argv)

    if args.class_name is None:
        args.class_name = args.source.stem

    source_text = args.source.read_text()
    transpiled = transpile_monolith(source_text, args.class_name)
    py_source = emit_python(transpiled, str(args.source))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(py_source)
    print(
        f"transpiled {args.source.name} → {args.output} ({len(transpiled.body_lines)} body statements)",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

