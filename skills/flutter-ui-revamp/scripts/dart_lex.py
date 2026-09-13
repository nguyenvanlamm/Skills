#!/usr/bin/env python3
"""Minimal Dart lexer shared by the flutter-ui-revamp scripts.

The only job here is to answer one question reliably: is this byte of the file
*code*, or is it inside a comment or a string literal? Every bulk edit and every
audit count in this skill depends on that answer. A naive regex over raw source
reports `Icons.home` inside a `// TODO: replace Icons.home` comment as a real
usage, and — much worse — a bulk replacer would rewrite it.

`strip(src)` returns source of identical length with every comment and every
string *body* blanked to spaces. Line numbers, column offsets and byte offsets
therefore survive untouched, so a match found in the stripped text can be
applied directly to the original.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

QUOTES = ("'", '"')


@dataclass
class StringLiteral:
    """A string literal found in the source, located for reporting."""

    value: str
    line: int
    start: int
    end: int


def _blank(chunk: str) -> str:
    """Replace a chunk with spaces, preserving newlines so lines still align."""
    return "".join("\n" if ch == "\n" else " " for ch in chunk)


def strip(src: str) -> Tuple[str, List[StringLiteral]]:
    """Blank out comments and string bodies.

    Returns (code_only, string_literals). `code_only` has exactly the same
    length as `src`.
    """
    out: List[str] = []
    strings: List[StringLiteral] = []
    i, n, line = 0, len(src), 1

    while i < n:
        ch = src[i]

        if ch == "\n":
            out.append("\n")
            line += 1
            i += 1
            continue

        # Line comment
        if ch == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            j = n if j == -1 else j
            out.append(_blank(src[i:j]))
            i = j
            continue

        # Block comment. Dart nests them, so count depth rather than
        # find('*/') — an unbalanced scan swallows the rest of the file.
        if ch == "/" and i + 1 < n and src[i + 1] == "*":
            depth, j = 1, i + 2
            while j < n and depth:
                if src.startswith("/*", j):
                    depth += 1
                    j += 2
                elif src.startswith("*/", j):
                    depth -= 1
                    j += 2
                else:
                    j += 1
            chunk = src[i:j]
            out.append(_blank(chunk))
            line += chunk.count("\n")
            i = j
            continue

        # String literal, with optional r (raw) prefix
        raw = False
        q_at = i
        if ch == "r" and i + 1 < n and src[i + 1] in QUOTES:
            raw = True
            q_at = i + 1

        if src[q_at] in QUOTES:
            quote = src[q_at]
            triple = src.startswith(quote * 3, q_at)
            delim = quote * 3 if triple else quote
            body_start = q_at + len(delim)
            j = body_start
            while j < n:
                if not raw and src[j] == "\\":
                    j += 2
                    continue
                if not triple and src[j] == "\n":
                    break  # unterminated single-line string; bail out safely
                if src.startswith(delim, j):
                    break
                j += 1
            body = src[body_start:j]
            end = min(j + len(delim), n)
            chunk = src[i:end]
            strings.append(StringLiteral(body, line, i, end))
            out.append(_blank(chunk))
            line += chunk.count("\n")
            i = end
            continue

        out.append(ch)
        i += 1

    return "".join(out), strings


def line_of(src: str, offset: int) -> int:
    """1-indexed line number containing `offset`."""
    return src.count("\n", 0, offset) + 1


if __name__ == "__main__":  # tiny self-test
    sample = '''
// Icons.home in a comment
final a = 'assets/images/logo.png';
/* block Icons.search */
Icon(Icons.settings);
'''
    code, lits = strip(sample)
    assert len(code) == len(sample)
    assert "Icons.home" not in code
    assert "Icons.search" not in code
    assert "Icons.settings" in code
    assert lits[0].value == "assets/images/logo.png"
    print("dart_lex self-test OK")
