"""
Unit tests for the Player class (game/player.py).

Run with:
    python -m pytest tests/test_player.py
or:
    python -m unittest tests.test_player
"""

import os
import sys
import unittest

# Allow running this test file directly (python tests/test_player.py)
# without needing the project installed as a package.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.player import Player


class TestPlayerCreation(unittest.TestCase):
    def test_valid_creation(self):
        player = Player("p1", "Sherlock")
        self.assertEqual(player.player_id, "p1")
        self.assertEqual(player.name, "Sherlock")
        self.assertEqual(player.cases_solved, 0)
        self.assertIsNone(player.current_case)
        self.assertEqual(player.collected_evidence, [])
        self.assertEqual(player.discovered_clues, [])
        self.assertEqual(player.investigation_score, 0)

    def test_empty_player_id_raises(self):
        with self.assertRaises(ValueError):
            Player("", "Sherlock")

    def test_empty_name_raises(self):
        with self.assertRaises(ValueError):
            Player("p1", "")

    def test_non_string_player_id_raises(self):
        with self.assertRaises(ValueError):
            Player(123, "Sherlock")

    def test_non_string_name_raises(self):
        with self.assertRaises(ValueError):
            Player("p1", None)


class TestCaseLifecycle(unittest.TestCase):
    def setUp(self):
        self.player = Player("p1", "Sherlock")

    def test_start_case(self):
        self.player.start_case("case_001")
        self.assertEqual(self.player.current_case, "case_001")

    def test_start_case_empty_id_raises(self):
        with self.assertRaises(ValueError):
            self.player.start_case("")

    def test_start_case_while_active_raises(self):
        self.player.start_case("case_001")
        with self.assertRaises(RuntimeError):
            self.player.start_case("case_002")

    def test_complete_case(self):
        self.player.start_case("case_001")
        self.player.add_evidence("bloody knife")
        self.player.add_clue("footprint")

        completed = self.player.complete_case()

        self.assertEqual(completed, "case_001")
        self.assertEqual(self.player.cases_solved, 1)
        self.assertIsNone(self.player.current_case)
        self.assertEqual(self.player.collected_evidence, [])
        self.assertEqual(self.player.discovered_clues, [])

    def test_complete_case_without_active_case_raises(self):
        with self.assertRaises(RuntimeError):
            self.player.complete_case()

    def test_starting_new_case_resets_evidence_and_clues(self):
        self.player.start_case("case_001")
        self.player.add_evidence("bloody knife")
        self.player.add_clue("footprint")
        self.player.complete_case()

        self.player.start_case("case_002")
        self.assertEqual(self.player.collected_evidence, [])
        self.assertEqual(self.player.discovered_clues, [])


class TestEvidenceAndClues(unittest.TestCase):
    def setUp(self):
        self.player = Player("p1", "Sherlock")
        self.player.start_case("case_001")

    def test_add_evidence(self):
        self.player.add_evidence("bloody knife")
        self.assertIn("bloody knife", self.player.collected_evidence)

    def test_add_duplicate_evidence_not_added_twice(self):
        self.player.add_evidence("bloody knife")
        self.player.add_evidence("bloody knife")
        self.assertEqual(self.player.collected_evidence.count("bloody knife"), 1)

    def test_add_empty_evidence_raises(self):
        with self.assertRaises(ValueError):
            self.player.add_evidence("")

    def test_add_evidence_without_active_case_raises(self):
        player = Player("p2", "Watson")
        with self.assertRaises(RuntimeError):
            player.add_evidence("bloody knife")

    def test_add_clue(self):
        self.player.add_clue("footprint")
        self.assertIn("footprint", self.player.discovered_clues)

    def test_add_duplicate_clue_not_added_twice(self):
        self.player.add_clue("footprint")
        self.player.add_clue("footprint")
        self.assertEqual(self.player.discovered_clues.count("footprint"), 1)

    def test_add_empty_clue_raises(self):
        with self.assertRaises(ValueError):
            self.player.add_clue("")

    def test_add_clue_without_active_case_raises(self):
        player = Player("p2", "Watson")
        with self.assertRaises(RuntimeError):
            player.add_clue("footprint")


class TestScore(unittest.TestCase):
    def setUp(self):
        self.player = Player("p1", "Sherlock")

    def test_update_score_positive(self):
        self.player.update_score(10)
        self.assertEqual(self.player.investigation_score, 10)

    def test_update_score_negative_floors_at_zero(self):
        self.player.update_score(5)
        self.player.update_score(-20)
        self.assertEqual(self.player.investigation_score, 0)

    def test_update_score_non_int_raises(self):
        with self.assertRaises(ValueError):
            self.player.update_score(3.5)

    def test_update_score_bool_raises(self):
        # bool is technically an int subclass in Python; explicitly rejected.
        with self.assertRaises(ValueError):
            self.player.update_score(True)


class TestProgress(unittest.TestCase):
    def test_get_progress_snapshot(self):
        player = Player("p1", "Sherlock")
        player.start_case("case_001")
        player.add_evidence("bloody knife")
        player.add_clue("footprint")
        player.update_score(15)

        progress = player.get_progress()

        self.assertEqual(progress["player_id"], "p1")
        self.assertEqual(progress["name"], "Sherlock")
        self.assertEqual(progress["cases_solved"], 0)
        self.assertEqual(progress["current_case"], "case_001")
        self.assertEqual(progress["evidence_count"], 1)
        self.assertEqual(progress["clues_count"], 1)
        self.assertEqual(progress["investigation_score"], 15)


if __name__ == "__main__":
    unittest.main()
