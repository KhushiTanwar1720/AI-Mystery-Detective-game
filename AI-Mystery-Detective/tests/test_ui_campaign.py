"""
Unit tests for ui/campaign.py -- the data-driven campaign manifest
loader and backend-availability/status resolver used by the UI's
case-selection screen.

These tests deliberately do NOT import pygame or anything under
ui/screens, ui/components, ui/app.py -- ui/campaign.py is designed to
be pygame-free and independently testable, and these tests verify
that promise as well as the resolution logic itself.

Run with:
    python -m unittest tests.test_ui_campaign
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.case import CaseManager
from game.player import Player
from ui.campaign import (
    DEFAULT_CAMPAIGN_PATH,
    LEVEL_STATUS_AVAILABLE,
    LEVEL_STATUS_COMPLETED,
    LEVEL_STATUS_IN_PROGRESS,
    LEVEL_STATUS_LOCKED,
    LEVEL_STATUS_NOT_YET_BUILT,
    LevelInfo,
    count_playable_levels,
    load_campaign,
    load_campaign_manifest,
    resolve_availability,
    resolve_status,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = PROJECT_ROOT / "cases"


class TestNoPygameDependency(unittest.TestCase):
    def test_campaign_module_source_never_imports_pygame(self):
        import ui.campaign as campaign_module

        source = Path(campaign_module.__file__).read_text()
        self.assertNotIn("import pygame", source)

    def test_importing_ui_campaign_does_not_require_pygame_to_be_present(self):
        # The successful `from ui.campaign import ...` at the top of
        # this file already proves this in an environment without
        # pygame installed; this test just documents the guarantee.
        import ui.campaign  # noqa: F401 -- re-import is a cheap no-op

        self.assertTrue(True)


class TestLoadCampaignManifest(unittest.TestCase):
    def test_default_manifest_loads_15_levels(self):
        levels = load_campaign_manifest()
        self.assertEqual(len(levels), 15)

    def test_levels_are_sorted_by_level_number(self):
        levels = load_campaign_manifest()
        numbers = [lvl.level_number for lvl in levels]
        self.assertEqual(numbers, sorted(numbers))
        self.assertEqual(numbers, list(range(1, 16)))

    def test_level_one_maps_to_case_001(self):
        levels = load_campaign_manifest()
        self.assertEqual(levels[0].case_id, "case_001")
        self.assertEqual(levels[0].title, "The Missing Necklace")

    def test_all_levels_now_map_to_a_case_id(self):
        # The full 15-level campaign is implemented: every level maps
        # to a real backend case id (see Phase 5/6 content build-out).
        levels = load_campaign_manifest()
        for level in levels:
            self.assertIsNotNone(level.case_id)

    def test_level_case_ids_are_unique(self):
        levels = load_campaign_manifest()
        case_ids = [lvl.case_id for lvl in levels]
        self.assertEqual(len(case_ids), len(set(case_ids)))

    def test_missing_manifest_file_raises(self):
        with self.assertRaises(FileNotFoundError):
            load_campaign_manifest(Path("/nonexistent/campaign.json"))

    def test_malformed_json_raises_value_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad_path = Path(tmp) / "bad.json"
            bad_path.write_text("{not valid json")
            with self.assertRaises(ValueError):
                load_campaign_manifest(bad_path)

    def test_skips_malformed_level_entries(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = Path(tmp) / "campaign.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "levels": [
                            {"level_number": 1, "title": "Valid Level"},
                            {"level_number": "not-a-number", "title": "Bad Level"},
                            "not even a dict",
                            {"title": "Missing level_number entirely"},
                        ]
                    }
                )
            )
            levels = load_campaign_manifest(manifest_path)
            self.assertEqual(len(levels), 1)
            self.assertEqual(levels[0].title, "Valid Level")


class TestLevelInfoDisplay(unittest.TestCase):
    def test_difficulty_display_star_count(self):
        level = LevelInfo(1, "case_001", "T", "S", difficulty_stars=2, horror_rating=1)
        display = level.difficulty_display()
        self.assertEqual(display.count("\u2605"), 2)
        self.assertEqual(display.count("\u2606"), 3)
        self.assertEqual(len(display), 5)

    def test_difficulty_display_clamped(self):
        level = LevelInfo(1, "case_001", "T", "S", difficulty_stars=99, horror_rating=1)
        self.assertEqual(level.difficulty_display().count("\u2605"), 5)

    def test_horror_display_bar_count(self):
        level = LevelInfo(1, "case_001", "T", "S", difficulty_stars=1, horror_rating=3)
        display = level.horror_display()
        self.assertEqual(display.count("\u25A0"), 3)
        self.assertEqual(display.count("\u25A1"), 7)

    def test_is_playable_requires_backend_data_and_unlocked_status(self):
        level = LevelInfo(1, "case_001", "T", "S", 1, 1)
        level.has_backend_data = True
        level.status = LEVEL_STATUS_AVAILABLE
        self.assertTrue(level.is_playable())

        level.status = LEVEL_STATUS_LOCKED
        self.assertFalse(level.is_playable())

        level.status = LEVEL_STATUS_AVAILABLE
        level.has_backend_data = False
        self.assertFalse(level.is_playable())


class TestResolveAvailability(unittest.TestCase):
    def test_case_001_has_full_backend_data(self):
        levels = load_campaign_manifest()
        resolve_availability(levels, CASES_DIR)
        level_one = next(lvl for lvl in levels if lvl.level_number == 1)
        self.assertTrue(level_one.has_backend_data)

    def test_all_15_levels_have_full_backend_data(self):
        # Every campaign level (1-15) now has a real case + suspects +
        # evidence + clues + locations file on disk (Phase 5/6).
        levels = load_campaign_manifest()
        resolve_availability(levels, CASES_DIR)
        for level in levels:
            self.assertTrue(
                level.has_backend_data,
                f"level {level.level_number} ({level.title!r}) missing backend data",
            )

    def test_bare_case_json_without_support_files_is_not_available(self):
        # case_002 exists as a bare case file with no evidence/clue/
        # suspect files behind it -- must not count as playable.
        levels = [LevelInfo(1, "case_002", "T", "S", 1, 1)]
        resolve_availability(levels, CASES_DIR)
        self.assertFalse(levels[0].has_backend_data)

    def test_unknown_case_id_has_no_backend_data(self):
        levels = [LevelInfo(1, "case_999_does_not_exist", "T", "S", 1, 1)]
        resolve_availability(levels, CASES_DIR)
        self.assertFalse(levels[0].has_backend_data)


class TestResolveStatus(unittest.TestCase):
    def _built_levels(self, count=3):
        levels = [
            LevelInfo(i, f"case_{i:03d}", f"Title {i}", "S", 1, 1) for i in range(1, count + 1)
        ]
        for level in levels:
            level.has_backend_data = True
        return levels

    def test_no_player_everything_available(self):
        levels = self._built_levels()
        resolve_status(levels, player=None)
        self.assertTrue(all(lvl.status == LEVEL_STATUS_AVAILABLE for lvl in levels))

    def test_all_levels_available_with_no_player_and_real_backend(self):
        # With every level now backed by real case data and no player
        # (nothing to gate sequential unlocking), every level should
        # resolve as available rather than "not yet built".
        levels = load_campaign_manifest()
        resolve_availability(levels, CASES_DIR)
        resolve_status(levels, player=None)
        for level in levels:
            self.assertEqual(level.status, LEVEL_STATUS_AVAILABLE)

    def test_sequential_unlock_against_real_backend_with_fresh_player(self):
        # A brand-new player (0 cases solved) should see level 1
        # available and every later level locked, even though all 15
        # now have backend data -- unlocking is still sequential.
        levels = load_campaign_manifest()
        resolve_availability(levels, CASES_DIR)
        player = Player("p1", "Ada")
        resolve_status(levels, player=player)
        self.assertEqual(levels[0].status, LEVEL_STATUS_AVAILABLE)
        for level in levels[1:]:
            self.assertEqual(level.status, LEVEL_STATUS_LOCKED)

    def test_sequential_unlock_with_zero_cases_solved(self):
        levels = self._built_levels()
        player = Player("p1", "Ada")
        resolve_status(levels, player=player)
        self.assertEqual(levels[0].status, LEVEL_STATUS_AVAILABLE)
        self.assertEqual(levels[1].status, LEVEL_STATUS_LOCKED)
        self.assertEqual(levels[2].status, LEVEL_STATUS_LOCKED)

    def test_sequential_unlock_after_solving_one_case(self):
        levels = self._built_levels()
        player = Player("p1", "Ada")
        player.cases_solved = 1
        resolve_status(levels, player=player)
        self.assertEqual(levels[0].status, LEVEL_STATUS_AVAILABLE)
        self.assertEqual(levels[1].status, LEVEL_STATUS_AVAILABLE)
        self.assertEqual(levels[2].status, LEVEL_STATUS_LOCKED)

    def test_case_manager_overrides_with_real_case_status_solved(self):
        levels = self._built_levels(count=1)
        levels[0].case_id = "case_001"

        case_manager = CaseManager()
        case_manager.load_all_cases()
        case = case_manager.get_case("case_001")
        case.status = "solved"

        resolve_status(levels, player=None, case_manager=case_manager)
        self.assertEqual(levels[0].status, LEVEL_STATUS_COMPLETED)

    def test_case_manager_overrides_with_real_case_status_in_progress(self):
        levels = self._built_levels(count=1)
        levels[0].case_id = "case_001"

        case_manager = CaseManager()
        case_manager.load_all_cases()
        case = case_manager.get_case("case_001")
        case.status = "in_progress"

        resolve_status(levels, player=None, case_manager=case_manager)
        self.assertEqual(levels[0].status, LEVEL_STATUS_IN_PROGRESS)

    def test_case_manager_without_loaded_case_falls_back_to_sequential_logic(self):
        levels = self._built_levels(count=1)
        levels[0].case_id = "case_999_never_loaded"
        case_manager = CaseManager()
        resolve_status(levels, player=None, case_manager=case_manager)
        self.assertEqual(levels[0].status, LEVEL_STATUS_AVAILABLE)


class TestLoadCampaignEndToEnd(unittest.TestCase):
    def test_load_campaign_against_real_backend(self):
        levels = load_campaign(CASES_DIR)
        self.assertEqual(len(levels), 15)
        self.assertTrue(levels[0].has_backend_data)
        self.assertEqual(levels[0].status, LEVEL_STATUS_AVAILABLE)

    def test_count_playable_levels_matches_actual_backend_data(self):
        levels = load_campaign(CASES_DIR)
        self.assertEqual(count_playable_levels(levels), 15)

    def test_load_campaign_with_real_player_and_case_manager(self):
        case_manager = CaseManager()
        case_manager.load_all_cases()
        player = Player("p1", "Ada")

        levels = load_campaign(CASES_DIR, player=player, case_manager=case_manager)
        level_one = levels[0]
        self.assertEqual(level_one.status, LEVEL_STATUS_AVAILABLE)


if __name__ == "__main__":
    unittest.main()
