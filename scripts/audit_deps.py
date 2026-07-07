"""
audit_deps.py - the dependency-audit gate.

Checks the project's declared dependencies (requirements.txt, plus their whole
transitive closure) against known-vulnerability databases via `pip-audit`. A
flagged package means a dependency has a published CVE / advisory, so we learn
about it on a PR rather than in production.

Why this gate is CI-only, not a pytest test (unlike the microcopy and retrieval
gates): those are deterministic and run offline, so they belong in the test
suite. A dependency audit is inherently ONLINE (it queries a live advisory feed)
and TIME-VARYING (a clean tree today can flag tomorrow when a new CVE lands, with
no code change). Wiring that into `pytest` would make the offline test suite
flaky and network-dependent. So it runs as its own CI step and as this one-command
local check.

Run it:  python scripts/audit_deps.py
Waiving an unfixable/false-positive advisory (documented, deliberate):
         python scripts/audit_deps.py --ignore-vuln GHSA-xxxx-xxxx-xxxx
(any extra args are passed straight through to pip-audit).
"""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REQUIREMENTS = os.path.join(ROOT, "requirements.txt")


def main() -> int:
    cmd = [
        sys.executable, "-m", "pip_audit",
        "-r", REQUIREMENTS,
        "--progress-spinner", "off",
    ] + sys.argv[1:]

    try:
        result = subprocess.run(cmd)
    except FileNotFoundError:
        print(
            "dependency audit: pip-audit is not installed. Install it with "
            "`pip install pip-audit`, then re-run `python scripts/audit_deps.py`."
        )
        return 1

    if result.returncode == 0:
        print("dependency audit: clean (no known vulnerabilities in requirements).")
    else:
        print(
            "dependency audit: FAIL. A dependency has a known vulnerability (see "
            "above). Bump the affected package in requirements.txt, or, if there is "
            "no fix yet, waive it deliberately with `--ignore-vuln <ID>` and a note."
        )
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())
