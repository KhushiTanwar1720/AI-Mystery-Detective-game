"""
Small standalone example showing how to use Clue and ClueManager,
including cross-referencing discovered clues with evidence/suspects.

Run with:
    python examples/clue_example.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.clue import ClueManager
from game.evidence import EvidenceManager


def main() -> None:
    clue_manager = ClueManager(clues_dir="cases/clues")
    clue_manager.load_all_clues()

    evidence_manager = EvidenceManager(evidence_dir="cases/evidence")
    evidence_manager.load_all_evidence()

    print(f"Loaded {len(clue_manager)} clue(s), {len(evidence_manager)} evidence item(s)")
    for error in clue_manager.get_load_errors():
        print(f"  [clue load error] {error}")

    clue = clue_manager.get_clue("clue_silver_smell")
    if clue is None:
        print("Clue not found.")
        return

    print("\nBefore discovery, get_info() withholds the solution-relevant fields:")
    print(clue.get_info())

    clue_manager.discover_clue("clue_silver_smell")
    evidence_manager.discover_evidence("evidence_silver_polish_rag")

    print("\nAfter discovery, full details are revealed:")
    print(clue.get_info())

    linked = clue_manager.get_clues_by_suspect("Butler James")
    print(f"\nDiscovered clues linked to Butler James: {[c.clue_id for c in linked]}")


if __name__ == "__main__":
    main()
