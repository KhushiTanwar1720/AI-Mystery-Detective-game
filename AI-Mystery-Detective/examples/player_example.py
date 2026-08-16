"""
Small standalone example showing how to instantiate and use Player.

Run with:
    python examples/player_example.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.player import Player


def main() -> None:
    player = Player(player_id="p001", name="Sherlock")

    player.start_case("case_001")
    player.add_evidence("bloody knife")
    player.add_clue("muddy footprint near the window")
    player.update_score(20)

    print("Progress mid-case:", player.get_progress())

    solved_case = player.complete_case()
    print(f"Solved: {solved_case}")
    print("Progress after completion:", player.get_progress())


if __name__ == "__main__":
    main()
