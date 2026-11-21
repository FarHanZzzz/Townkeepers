"""Reconcile @pytest.mark.req IDs in tests with GRAND_PRD.md (TECHNICAL_REQUIREMENTS.md section 7, CI).

Usage:
    uv run python tools/check_req_markers.py            # fail on unknown IDs, print coverage summary
    uv run python tools/check_req_markers.py --markdown # also print an ID -> tests table
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ID_PATTERN = re.compile(r"\b(FR-[A-Z]{3}-\d{2}|NFR-[A-Z]{3}-\d{2}|UC-\d{2}|AC-\d{2}|BR-\d{2})\b")


def prd_ids() -> set[str]:
    return set(ID_PATTERN.findall((ROOT / "GRAND_PRD.md").read_text(encoding="utf-8")))


def test_markers() -> dict[str, set[str]]:
    """Map requirement ID -> set of 'path::test_name'."""
    found: dict[str, set[str]] = defaultdict(set)
    for path in sorted((ROOT / "tests").rglob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue
            for deco in node.decorator_list:
                if (
                    isinstance(deco, ast.Call)
                    and isinstance(deco.func, ast.Attribute)
                    and deco.func.attr == "req"
                ):
                    for arg in deco.args:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            found[arg.value].add(
                                f"{path.relative_to(ROOT).as_posix()}::{node.name}"
                            )
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--markdown", action="store_true")
    args = parser.parse_args()
    known = prd_ids()
    markers = test_markers()
    unknown = sorted(set(markers) - known)
    if unknown:
        print("Unknown requirement IDs in test markers: " + ", ".join(unknown))
        return 1
    for prefix in ("FR-", "UC-", "AC-", "NFR-", "BR-"):
        ids = sorted(i for i in known if i.startswith(prefix))
        covered = [i for i in ids if i in markers]
        print(f"{prefix.rstrip('-'):>3}: {len(covered)}/{len(ids)} referenced by tests")
    if args.markdown:
        print("\n| Requirement | Tests |\n|---|---|")
        for rid in sorted(markers):
            print(f"| {rid} | {'<br>'.join(sorted(markers[rid]))} |")
    return 0


if __name__ == "__main__":
    sys.exit(main())
