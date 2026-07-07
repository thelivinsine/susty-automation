"""
lint_microcopy.py - guard the house style on visible copy.

The owner's standing rule (docs/WORKING_PREFERENCES.md): no em dashes in any
string the user can see. This gate encodes that as code so a stray em dash
cannot ship again.

What it checks, and why the boundary sits where it does:

- Python (.py): only STRING LITERALS that reach a user (report notes, UI
  labels, explanations, printed output). Module/function/class docstrings and
  comments are developer annotations, not visible product copy, so they are
  exempt. This matches the convention already in the repo: docs are clean,
  code comments are not.
- Markdown (.md): the whole document. README and CLAUDE.md are visible.
- Allowlisted files (ALLOWLIST): skipped entirely. The synthetic data
  generator deliberately mimics DEFRA's real workbook formatting, and real
  DEFRA data itself contains em dashes. That is third-party layout, not our
  copy.

Run it directly (`python scripts/lint_microcopy.py`) or via pytest. Exits
non-zero and prints every violation as `path:line: snippet`.
"""

import ast
import os
import sys

# Em dash (U+2014) and horizontal bar (U+2015). The en dash (U+2013) and the
# bullet are explicitly allowed by the house style, so they are not listed.
# Defined by code point so the banned characters never appear as literals here
# (otherwise this file would flag itself).
BANNED = {chr(0x2014): "em dash", chr(0x2015): "horizontal bar"}

# Files that mirror third-party (DEFRA) formatting, not our own copy.
ALLOWLIST = {
    os.path.join("scripts", "make_synthetic_data.py"),
}

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _banned_in(text):
    """Return the list of banned characters found in a piece of text."""
    return [name for ch, name in BANNED.items() if ch in text]


def _docstring_nodes(tree):
    """Ids of string nodes that are docstrings (exempt developer annotations)."""
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = getattr(node, "body", [])
            first = body[0] if body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                ids.add(id(first.value))
    return ids


def check_python(path, source):
    """Flag banned characters in user-facing string literals only."""
    violations = []
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [(getattr(exc, "lineno", 0), f"could not parse: {exc.msg}")]
    docstrings = _docstring_nodes(tree)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
        ):
            found = _banned_in(node.value)
            if found:
                snippet = node.value.strip().replace("\n", " ")[:70]
                violations.append((node.lineno, f"{', '.join(found)} in string: {snippet!r}"))
    return violations


def check_markdown(path, source):
    """Flag banned characters anywhere in a visible document."""
    violations = []
    for i, line in enumerate(source.splitlines(), start=1):
        found = _banned_in(line)
        if found:
            violations.append((i, f"{', '.join(found)} in: {line.strip()[:70]!r}"))
    return violations


def iter_target_files():
    """Yield tracked .py and .md files under the repo, skipping noise dirs."""
    skip_dirs = {".git", "__pycache__", ".pytest_cache", "data"}
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in skip_dirs]
        for name in filenames:
            if name.endswith((".py", ".md")):
                yield os.path.join(dirpath, name)


def lint(paths=None):
    """Return a list of (relpath, lineno, message) violations."""
    files = paths if paths else sorted(iter_target_files())
    all_violations = []
    for path in files:
        rel = os.path.relpath(path, ROOT)
        if rel in ALLOWLIST:
            continue
        with open(path, encoding="utf-8") as fh:
            source = fh.read()
        if path.endswith(".py"):
            found = check_python(path, source)
        else:
            found = check_markdown(path, source)
        for lineno, msg in found:
            all_violations.append((rel, lineno, msg))
    return all_violations


def main():
    args = sys.argv[1:]
    violations = lint(args or None)
    if not violations:
        print("microcopy lint: clean (no em dashes in visible copy)")
        return 0
    for rel, lineno, msg in violations:
        print(f"{rel}:{lineno}: {msg}")
    print(f"\nmicrocopy lint: {len(violations)} violation(s). "
          "Rewrite with a comma, colon, period, or parentheses (en dash is fine).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
