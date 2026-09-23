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

from bisect import bisect_left
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


def strip(src: str) -> Tuple[str, List[StringLiteral]]:
    """Blank out comments and string bodies.

    Returns (code_only, string_literals). `code_only` has exactly the same
    length as `src`. The inside of a `${...}` interpolation is code, not string,
    so it stays visible: `'${Icons.home.codePoint}'` counts as a real usage and
    is rewritten by the bulk replacer like any other.
    """
    out = list(src)
    strings: List[StringLiteral] = []
    n = len(src)
    newlines = [k for k, c in enumerate(src) if c == "\n"]

    def blank(a: int, b: int) -> None:
        for k in range(a, min(b, n)):
            if out[k] != "\n":
                out[k] = " "

    def scan_code(i: int, in_interp: bool) -> int:
        """Scan code from i. Inside an interpolation, stop at the matching `}`
        and return its offset; at top level, return n."""
        depth = 0
        while i < n:
            ch = src[i]
            if ch == "/" and src.startswith("//", i):
                j = src.find("\n", i)
                j = n if j == -1 else j
                blank(i, j)
                i = j
                continue
            # Block comment. Dart nests them, so count depth rather than
            # find('*/') — an unbalanced scan swallows the rest of the file.
            if ch == "/" and src.startswith("/*", i):
                d, j = 1, i + 2
                while j < n and d:
                    if src.startswith("/*", j):
                        d, j = d + 1, j + 2
                    elif src.startswith("*/", j):
                        d, j = d - 1, j + 2
                    else:
                        j += 1
                blank(i, j)
                i = j
                continue
            # String literal, with optional r (raw) prefix. The `r` must start a
            # token, or `bar'` in malformed code would be read as a raw string.
            prev_ident = i > 0 and (src[i - 1].isalnum() or src[i - 1] in "_$")
            if ch == "r" and not prev_ident and i + 1 < n and src[i + 1] in QUOTES:
                i = scan_string(i, i + 1, raw=True)
                continue
            if ch in QUOTES:
                i = scan_string(i, i, raw=False)
                continue
            if in_interp:
                if ch == "{":
                    depth += 1
                elif ch == "}":
                    if depth == 0:
                        return i
                    depth -= 1
            i += 1
        return n

    def scan_string(start: int, q_at: int, raw: bool) -> int:
        quote = src[q_at]
        triple = src.startswith(quote * 3, q_at)
        delim = quote * 3 if triple else quote
        body_start = q_at + len(delim)
        j = body_start
        blank(start, body_start)
        while j < n:
            if not raw and src[j] == "\\":
                blank(j, j + 2)
                j += 2
                continue
            if not triple and src[j] == "\n":
                break  # unterminated single-line string; bail out safely
            if src.startswith(delim, j):
                break
            if not raw and src.startswith("${", j):
                blank(j, j + 2)
                close = scan_code(j + 2, in_interp=True)
                blank(close, close + 1)
                j = close + 1
                continue
            blank(j, j + 1)
            j += 1
        end = min(j + len(delim), n)
        blank(j, end)
        strings.append(StringLiteral(src[body_start:j], bisect_left(newlines, start) + 1,
                                     start, end))
        return end

    scan_code(0, in_interp=False)
    strings.sort(key=lambda s: s.start)
    return "".join(out), strings


def line_of(src: str, offset: int) -> int:
    """1-indexed line number containing `offset`."""
    return src.count("\n", 0, offset) + 1


if __name__ == "__main__":  # tiny self-test
    sample = '''
// Icons.home in a comment
final a = 'assets/images/logo.png';
/* block Icons.search /* nested Icons.close */ still Icons.edit */
Icon(Icons.settings);
final s = 'cp ${Icons.star.codePoint} and ${m['k']} not Icons.add';
final r = r'raw ${Icons.delete}';
'''
    code, lits = strip(sample)
    assert len(code) == len(sample)
    assert code.count("\n") == sample.count("\n")
    for gone in ("Icons.home", "Icons.search", "Icons.close", "Icons.edit",
                 "Icons.add", "Icons.delete"):
        assert gone not in code, gone
    assert "Icons.settings" in code
    assert "Icons.star.codePoint" in code
    assert "m[" in code and "Icons.add" not in code
    assert lits[0].value == "assets/images/logo.png"
    assert any(l.value == "k" for l in lits)
    print("dart_lex self-test OK")
