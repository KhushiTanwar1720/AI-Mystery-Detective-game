"""
Small standalone example showing how to use Evidence and
EvidenceManager, including how info is withheld until discovery.

Run with:
    python examples/evidence_example.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.evidence import EvidenceManager


def main() -> None:
    manager = EvidenceManager(evidence_dir="cases/evidence")
    manager.load_all_evidence()

    print(f"Loaded {len(manager)} evidence item(s)")
    for error in manager.get_load_errors():
        print(f"  [load error] {error}")

    print(f"\nUndiscovered so far: {len(manager.get_undiscovered_evidence())}")

    rag = manager.get_evidence("evidence_silver_polish_rag")
    if rag is None:
        print("Evidence not found.")
        return

    print("\nBefore discovery, get_info() withholds the solution-relevant fields:")
    print(rag.get_info())

    manager.discover_evidence("evidence_silver_polish_rag")

    print("\nAfter discovery, full details are revealed:")
    print(rag.get_info())

    linked = manager.get_evidence_by_suspect("Butler James")
    print(f"\nDiscovered evidence linked to Butler James: {[e.name for e in linked]}")


if __name__ == "__main__":
    main()
