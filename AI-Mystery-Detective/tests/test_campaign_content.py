"""
Regression tests for the full 15-level campaign content (Phase 5/6/19/20
of the completion pass).

These tests verify that every level in data/campaign.json maps to a
real, fully playable case: the case file loads, every suspect/
evidence/clue/location reference resolves, the location graph is
connected, and the case can actually be solved end-to-end through
GameController with its own correct_suspect.

Run with:
    python -m unittest tests.test_campaign_content
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.game_controller import GameController
from ui.campaign import load_campaign_manifest, resolve_availability

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = PROJECT_ROOT / "cases"


class TestCampaignLevelCount(unittest.TestCase):
    def test_exactly_15_levels_defined(self):
        levels = load_campaign_manifest()
        self.assertEqual(len(levels), 15)

    def test_every_level_has_a_unique_case_id(self):
        levels = load_campaign_manifest()
        ids = [lvl.case_id for lvl in levels]
        self.assertTrue(all(ids))
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_level_has_full_backend_data(self):
        levels = load_campaign_manifest()
        resolve_availability(levels, CASES_DIR)
        for level in levels:
            self.assertTrue(
                level.has_backend_data,
                f"Level {level.level_number} ({level.title!r}) is missing backend data",
            )

    def test_horror_rating_progresses_across_the_campaign(self):
        # Not strictly monotonic level-to-level (a couple of levels
        # share a rating by design), but the campaign as a whole must
        # trend upward from level 1 to level 15.
        levels = load_campaign_manifest()
        self.assertEqual(levels[0].horror_rating, 1)
        self.assertGreaterEqual(levels[-1].horror_rating, 9)
        self.assertLessEqual(levels[0].horror_rating, levels[-1].horror_rating)

    def test_locations_are_not_identical_reused_lists_across_levels(self):
        # Each level's flavor location names shouldn't be a verbatim
        # copy of another level's -- i.e. every level has its own setting.
        levels = load_campaign_manifest()
        seen = set()
        for level in levels:
            key = tuple(level.locations)
            self.assertNotIn(key, seen, f"Level {level.level_number} reuses another level's location list")
            seen.add(key)


def _playthrough(case_id: str) -> dict:
    """Fully play a case end-to-end via GameController and return the result."""
    gc = GameController(player_id="tester", player_name="Tester", cases_dir=str(CASES_DIR))
    gc.start_investigation(case_id)
    case = gc.case
    for loc in gc.get_available_locations():
        gc.explore_location_by_id(loc.location_id)
    for eid in list(case.evidence):
        gc.discover_evidence(eid)
    for cid in list(case.clues):
        gc.discover_clue(cid)
    for suspect in gc.get_case_suspects():
        gc.start_interrogation(suspect.suspect_id)
        q = gc.ask_question("Where were you at the time of the incident?", category="alibi")
        gc.record_answer(q.question_id, suspect.alibi)
        gc.end_interrogation()
    gc.run_ai_analysis()
    return gc.conclude_case(case.correct_suspect)


class TestEveryLevelIsFullyPlayable(unittest.TestCase):
    """Parameterized-by-hand: one test method per campaign level so a
    failure clearly names which level broke, without relying on
    subTest-only visibility."""

    @classmethod
    def setUpClass(cls):
        cls.levels = {lvl.level_number: lvl for lvl in load_campaign_manifest()}

    def _check_level(self, level_number: int):
        level = self.levels[level_number]
        gc = GameController(player_id="tester", player_name="Tester", cases_dir=str(CASES_DIR))
        case = gc.load_case(level.case_id)

        # Referential integrity: every suspect on the case resolves.
        suspects = gc.get_case_suspects()
        names = {s.name for s in suspects}
        self.assertEqual(len(suspects), len(case.suspects))
        self.assertIn(case.correct_suspect, names)

        # Location graph: every evidence/clue id used by the case is
        # actually placed somewhere reachable.
        locations = gc.location_manager.get_all_locations()
        self.assertGreaterEqual(len(locations), 3, f"level {level_number} has too few locations")
        placed_evidence = {eid for loc in locations for eid in loc.available_evidence}
        placed_clues = {cid for loc in locations for cid in loc.available_clues}
        for eid in case.evidence:
            self.assertIn(eid, placed_evidence)
        for cid in case.clues:
            self.assertIn(cid, placed_clues)

        # Full playthrough must resolve as solved with the case's own
        # correct_suspect -- proving the mystery is actually solvable.
        result = _playthrough(level.case_id)
        self.assertTrue(result["solved"], f"level {level_number} ({level.case_id}) did not resolve as solved")
        self.assertEqual(result["case_status"], "solved")

    def test_level_01(self):
        self._check_level(1)

    def test_level_02(self):
        self._check_level(2)

    def test_level_03(self):
        self._check_level(3)

    def test_level_04(self):
        self._check_level(4)

    def test_level_05(self):
        self._check_level(5)

    def test_level_06(self):
        self._check_level(6)

    def test_level_07(self):
        self._check_level(7)

    def test_level_08(self):
        self._check_level(8)

    def test_level_09(self):
        self._check_level(9)

    def test_level_10(self):
        self._check_level(10)

    def test_level_11(self):
        self._check_level(11)

    def test_level_12(self):
        self._check_level(12)

    def test_level_13(self):
        self._check_level(13)

    def test_level_14(self):
        self._check_level(14)

    def test_level_15(self):
        self._check_level(15)


class TestWrongAccusationFails(unittest.TestCase):
    """A mystery isn't real if any suspect works -- confirm accusing an
    innocent suspect in a couple of representative levels resolves as
    unsolved, proving the correct_suspect is actually load-bearing."""

    def test_level_5_wrong_accusation_is_not_solved(self):
        gc = GameController(player_id="tester2", player_name="Tester2", cases_dir=str(CASES_DIR))
        gc.start_investigation("case_006")
        case = gc.case
        for loc in gc.get_available_locations():
            gc.explore_location_by_id(loc.location_id)
        wrong_suspect = next(name for name in case.suspects if name != case.correct_suspect)
        result = gc.conclude_case(wrong_suspect)
        self.assertFalse(result["solved"])
        self.assertEqual(result["case_status"], "failed")

    def test_level_15_wrong_accusation_is_not_solved(self):
        gc = GameController(player_id="tester3", player_name="Tester3", cases_dir=str(CASES_DIR))
        gc.start_investigation("case_016")
        case = gc.case
        for loc in gc.get_available_locations():
            gc.explore_location_by_id(loc.location_id)
        wrong_suspect = next(name for name in case.suspects if name != case.correct_suspect)
        result = gc.conclude_case(wrong_suspect)
        self.assertFalse(result["solved"])
        self.assertEqual(result["case_status"], "failed")


class TestCampaignSaveLoadAcrossLevels(unittest.TestCase):
    """Confirm save/load survives mid-progress on a later campaign level,
    not just level 1."""

    def test_save_and_load_mid_level_10(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            gc = GameController(
                player_id="saver", player_name="Saver", cases_dir=str(CASES_DIR), saves_dir=tmp
            )
            gc.start_investigation("case_011")
            case = gc.case
            first_location = gc.get_available_locations()[0]
            gc.explore_location_by_id(first_location.location_id)
            some_evidence = case.evidence[0]
            gc.discover_evidence(some_evidence)

            self.assertTrue(gc.save_game("slot_1"))

            gc2 = GameController(
                player_id="saver", player_name="Saver", cases_dir=str(CASES_DIR), saves_dir=tmp
            )
            self.assertTrue(gc2.load_game("slot_1"))
            self.assertEqual(gc2.case.case_id, "case_011")
            self.assertIn(some_evidence, [e.evidence_id for e in gc2.evidence_manager.get_all_evidence() if e.discovered])


if __name__ == "__main__":
    unittest.main()
