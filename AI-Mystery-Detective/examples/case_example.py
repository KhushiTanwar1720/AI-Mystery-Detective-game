"""
Small standalone example showing how to use CaseManager and Case.

Run with:
    python examples/case_example.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.case import CaseManager


def main() -> None:
    # Defaults to loading from the project's cases/ directory.
    manager = CaseManager()
    loaded = manager.load_all_cases()

    print(f"Loaded {len(loaded)} case(s) from '{manager.cases_dir}'")
    for error in manager.get_load_errors():
        print(f"  [load error] {error}")

    case = manager.get_case("case_001")
    if case is None:
        print("case_001 not found.")
        return

    print("\nCase info (solution hidden):", case.get_info())

    case.start()
    case.add_clue("muddy footprints leading to the kitchen")
    case.add_evidence("silver polish rag found in Butler James's room")

    solved = case.complete_case("Butler James")
    print(f"\nAccusation correct? {solved}")
    print("Final status:", case.get_status())


if __name__ == "__main__":
    main()
