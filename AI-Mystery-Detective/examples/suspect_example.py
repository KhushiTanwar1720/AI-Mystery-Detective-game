"""
Small standalone example showing how to use Suspect and SuspectManager,
including cross-referencing suspects with a loaded Case.

Run with:
    python examples/suspect_example.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.case import CaseManager
from game.suspect import SuspectManager


def main() -> None:
    # Load the case (from cases/) and its suspects (from cases/suspects/).
    case_manager = CaseManager()
    case_manager.load_all_cases()
    case = case_manager.get_case("case_001")

    suspect_manager = SuspectManager(suspects_dir="cases/suspects")
    suspect_manager.load_all_suspects()

    print(f"Loaded {len(suspect_manager)} suspect(s)")
    for error in suspect_manager.get_load_errors():
        print(f"  [load error] {error}")

    # Cross-reference: which registered suspects belong to case_001?
    case_suspects = suspect_manager.get_suspects_for_case(case)
    print(f"\nSuspects for '{case.title}':")
    for suspect in case_suspects:
        print(f"  - {suspect.name} ({suspect.occupation})")

    butler = suspect_manager.get_suspect("suspect_butler_james")
    if butler is None:
        print("Butler James not found.")
        return

    butler.add_statement("I was polishing silverware all evening.")
    butler.record_behavior("Avoided eye contact when asked about the necklace.")
    butler.update_suspicion_level(30)

    print("\nButler James's profile:")
    print(butler.get_info())


if __name__ == "__main__":
    main()
