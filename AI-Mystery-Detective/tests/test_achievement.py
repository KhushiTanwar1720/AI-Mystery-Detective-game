"""
Unit and integration tests for the Achievement system
(game/achievement.py), plus its integration with GameController and
SaveManager.

Tests cover:
- Achievement creation, validation, serialization.
- AchievementManager creation, registration, retrieval.
- Duplicate achievement prevention.
- Unlocking, idempotency, and unlock timestamps.
- Requirement checking (including missing/incomplete stats).
- Multiple/simultaneous achievement checks.
- Locked/unlocked queries and progress snapshots.
- Reset behavior.
- Serialization/deserialization round-trips.
- GameController integration: discover_evidence/discover_clue/
  conclude_case trigger achievement checks correctly.
- Save/load persistence, including backward compatibility with saves
  that have no achievement data.

Run with:
    python -m unittest tests.test_achievement
"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.achievement import (
    Achievement,
    AchievementManager,
    create_default_achievements,
)
from game.game_controller import GameController
from game.save_manager import SaveManager


# ---------------------------------------------------------------------------
# Achievement
# ---------------------------------------------------------------------------


class TestAchievementCreation(unittest.TestCase):
    def test_valid_creation_defaults(self):
        achievement = Achievement(
            achievement_id="first_case",
            name="First Case",
            description="Complete your first case.",
            requirement=[{"stat": "cases_solved", "operator": ">=", "value": 1}],
        )
        self.assertEqual(achievement.achievement_id, "first_case")
        self.assertEqual(achievement.name, "First Case")
        self.assertFalse(achievement.unlocked)
        self.assertIsNone(achievement.unlocked_at)

    def test_empty_id_raises(self):
        with self.assertRaises(ValueError):
            Achievement("", "Name", "Desc", [])

    def test_non_string_name_raises(self):
        with self.assertRaises(ValueError):
            Achievement("id", 123, "Desc", [])

    def test_empty_description_raises(self):
        with self.assertRaises(ValueError):
            Achievement("id", "Name", "   ", [])

    def test_unlocked_not_bool_raises(self):
        with self.assertRaises(ValueError):
            Achievement("id", "Name", "Desc", [], unlocked="yes")

    def test_requirement_not_list_raises(self):
        with self.assertRaises(ValueError):
            Achievement("id", "Name", "Desc", requirement={"stat": "x"})

    def test_requirement_condition_not_dict_raises(self):
        with self.assertRaises(ValueError):
            Achievement("id", "Name", "Desc", requirement=["not a dict"])

    def test_requirement_missing_stat_raises(self):
        with self.assertRaises(ValueError):
            Achievement("id", "Name", "Desc", requirement=[{"operator": ">=", "value": 1}])

    def test_requirement_bad_operator_raises(self):
        with self.assertRaises(ValueError):
            Achievement(
                "id", "Name", "Desc",
                requirement=[{"stat": "score", "operator": "~=", "value": 1}],
            )

    def test_requirement_defaults_operator_to_eq(self):
        achievement = Achievement("id", "Name", "Desc", requirement=[{"stat": "solved", "value": True}])
        self.assertEqual(achievement.requirement[0]["operator"], "==")

    def test_requirement_none_becomes_empty_list(self):
        achievement = Achievement("id", "Name", "Desc", requirement=None)
        self.assertEqual(achievement.requirement, [])

    def test_unlocked_true_without_timestamp_still_unlocked(self):
        achievement = Achievement("id", "Name", "Desc", [], unlocked=True)
        self.assertTrue(achievement.unlocked)


class TestAchievementUnlocking(unittest.TestCase):
    def setUp(self):
        self.achievement = Achievement(
            "id", "Name", "Desc", [{"stat": "x", "operator": ">=", "value": 1}]
        )

    def test_unlock_sets_flag_and_timestamp(self):
        result = self.achievement.unlock()
        self.assertTrue(result)
        self.assertTrue(self.achievement.unlocked)
        self.assertIsNotNone(self.achievement.unlocked_at)
        self.assertTrue(self.achievement.is_unlocked())

    def test_unlock_timestamp_is_iso_format(self):
        self.achievement.unlock()
        # datetime.fromisoformat should parse it without raising
        from datetime import datetime

        parsed = datetime.fromisoformat(self.achievement.unlocked_at)
        self.assertIsNotNone(parsed.tzinfo)

    def test_unlock_already_unlocked_is_idempotent(self):
        self.achievement.unlock()
        first_ts = self.achievement.unlocked_at

        result = self.achievement.unlock()

        self.assertFalse(result)
        self.assertEqual(self.achievement.unlocked_at, first_ts)

    def test_reset_clears_unlock_state(self):
        self.achievement.unlock()
        self.achievement.reset()
        self.assertFalse(self.achievement.unlocked)
        self.assertIsNone(self.achievement.unlocked_at)


class TestAchievementSerialization(unittest.TestCase):
    def test_to_dict_contains_all_fields(self):
        achievement = Achievement(
            "id", "Name", "Desc", [{"stat": "x", "operator": ">=", "value": 1}]
        )
        achievement.unlock()
        data = achievement.to_dict()

        self.assertEqual(data["achievement_id"], "id")
        self.assertEqual(data["name"], "Name")
        self.assertEqual(data["description"], "Desc")
        self.assertEqual(data["requirement"], [{"stat": "x", "operator": ">=", "value": 1}])
        self.assertTrue(data["unlocked"])
        self.assertIsNotNone(data["unlocked_at"])

    def test_from_dict_round_trip(self):
        original = Achievement(
            "id", "Name", "Desc", [{"stat": "x", "operator": ">=", "value": 1}]
        )
        original.unlock()

        rebuilt = Achievement.from_dict(original.to_dict())

        self.assertEqual(rebuilt.achievement_id, original.achievement_id)
        self.assertEqual(rebuilt.unlocked, original.unlocked)
        self.assertEqual(rebuilt.unlocked_at, original.unlocked_at)
        self.assertEqual(rebuilt.requirement, original.requirement)

    def test_from_dict_missing_field_raises(self):
        with self.assertRaises(KeyError):
            Achievement.from_dict({"achievement_id": "id", "name": "Name"})

    def test_from_dict_defaults_applied(self):
        achievement = Achievement.from_dict(
            {"achievement_id": "id", "name": "Name", "description": "Desc"}
        )
        self.assertEqual(achievement.requirement, [])
        self.assertFalse(achievement.unlocked)
        self.assertIsNone(achievement.unlocked_at)

    def test_to_dict_requirement_is_a_copy(self):
        achievement = Achievement(
            "id", "Name", "Desc", [{"stat": "x", "operator": ">=", "value": 1}]
        )
        data = achievement.to_dict()
        data["requirement"][0]["value"] = 999
        self.assertEqual(achievement.requirement[0]["value"], 1)


class TestDefaultAchievements(unittest.TestCase):
    def test_creates_eight_default_achievements(self):
        achievements = create_default_achievements()
        self.assertEqual(len(achievements), 8)

    def test_default_achievement_ids_unique(self):
        achievements = create_default_achievements()
        ids = [a.achievement_id for a in achievements]
        self.assertEqual(len(ids), len(set(ids)))

    def test_default_achievements_start_locked(self):
        achievements = create_default_achievements()
        self.assertTrue(all(not a.unlocked for a in achievements))

    def test_default_achievements_are_independent_instances(self):
        first_batch = create_default_achievements()
        second_batch = create_default_achievements()
        first_batch[0].unlock()
        self.assertFalse(second_batch[0].unlocked)

    def test_expected_ids_present(self):
        ids = {a.achievement_id for a in create_default_achievements()}
        expected = {
            "first_case",
            "evidence_hunter",
            "clue_collector",
            "master_investigator",
            "no_hint_detective",
            "speed_detective",
            "perfect_investigation",
            "master_detective",
        }
        self.assertEqual(ids, expected)


# ---------------------------------------------------------------------------
# AchievementManager
# ---------------------------------------------------------------------------


class TestAchievementManagerCreation(unittest.TestCase):
    def test_default_construction_loads_default_set(self):
        manager = AchievementManager()
        self.assertEqual(len(manager.get_all_achievements()), 8)

    def test_construction_with_empty_list(self):
        manager = AchievementManager(achievements=[])
        self.assertEqual(manager.get_all_achievements(), [])

    def test_construction_with_custom_achievements(self):
        custom = [Achievement("a1", "A1", "D1", [])]
        manager = AchievementManager(achievements=custom)
        self.assertEqual(len(manager.get_all_achievements()), 1)


class TestAchievementManagerRegistration(unittest.TestCase):
    def setUp(self):
        self.manager = AchievementManager(achievements=[])

    def test_add_achievement(self):
        achievement = Achievement("a1", "A1", "D1", [])
        self.manager.add_achievement(achievement)
        self.assertIs(self.manager.get_achievement("a1"), achievement)

    def test_add_non_achievement_raises(self):
        with self.assertRaises(ValueError):
            self.manager.add_achievement({"achievement_id": "a1"})

    def test_add_duplicate_id_raises(self):
        self.manager.add_achievement(Achievement("a1", "A1", "D1", []))
        with self.assertRaises(ValueError):
            self.manager.add_achievement(Achievement("a1", "Dup", "D2", []))

    def test_get_unknown_achievement_returns_none(self):
        self.assertIsNone(self.manager.get_achievement("missing"))

    def test_get_all_achievements_returns_list(self):
        self.manager.add_achievement(Achievement("a1", "A1", "D1", []))
        self.manager.add_achievement(Achievement("a2", "A2", "D2", []))
        all_achievements = self.manager.get_all_achievements()
        self.assertEqual(len(all_achievements), 2)


class TestAchievementManagerRequirementChecking(unittest.TestCase):
    def setUp(self):
        self.manager = AchievementManager(achievements=[])

    def test_check_requirement_true_when_stat_meets_condition(self):
        achievement = Achievement(
            "a1", "A1", "D1", [{"stat": "cases_solved", "operator": ">=", "value": 1}]
        )
        self.assertTrue(self.manager.check_requirement(achievement, {"cases_solved": 1}))

    def test_check_requirement_false_when_stat_does_not_meet_condition(self):
        achievement = Achievement(
            "a1", "A1", "D1", [{"stat": "cases_solved", "operator": ">=", "value": 5}]
        )
        self.assertFalse(self.manager.check_requirement(achievement, {"cases_solved": 1}))

    def test_check_requirement_multiple_conditions_all_must_match(self):
        achievement = Achievement(
            "a1", "A1", "D1",
            [
                {"stat": "solved", "operator": "==", "value": True},
                {"stat": "accuracy", "operator": ">=", "value": 90.0},
            ],
        )
        self.assertTrue(
            self.manager.check_requirement(achievement, {"solved": True, "accuracy": 95.0})
        )
        self.assertFalse(
            self.manager.check_requirement(achievement, {"solved": True, "accuracy": 50.0})
        )
        self.assertFalse(
            self.manager.check_requirement(achievement, {"solved": False, "accuracy": 95.0})
        )

    def test_check_requirement_missing_stat_in_data_is_graceful(self):
        achievement = Achievement(
            "a1", "A1", "D1", [{"stat": "not_present", "operator": ">=", "value": 1}]
        )
        # Should not raise, and simply report unmet.
        self.assertFalse(self.manager.check_requirement(achievement, {}))

    def test_check_requirement_with_none_stats(self):
        achievement = Achievement(
            "a1", "A1", "D1", [{"stat": "cases_solved", "operator": ">=", "value": 1}]
        )
        self.assertFalse(self.manager.check_requirement(achievement, None))

    def test_check_requirement_no_conditions_is_always_true(self):
        achievement = Achievement("a1", "A1", "D1", [])
        self.assertTrue(self.manager.check_requirement(achievement, {}))

    def test_check_requirement_incomparable_types_is_graceful(self):
        achievement = Achievement(
            "a1", "A1", "D1", [{"stat": "rank", "operator": ">=", "value": 5}]
        )
        # rank is a string in real stats; comparing str >= int raises
        # TypeError internally -- must be handled, not propagated.
        self.assertFalse(
            self.manager.check_requirement(achievement, {"rank": "Detective Rookie"})
        )

    def test_all_operators(self):
        cases = [
            (">=", 5, 5, True),
            (">=", 4, 5, False),
            ("<=", 5, 5, True),
            ("<=", 6, 5, False),
            (">", 6, 5, True),
            (">", 5, 5, False),
            ("<", 4, 5, True),
            ("<", 5, 5, False),
            ("==", 5, 5, True),
            ("!=", 4, 5, True),
            ("!=", 5, 5, False),
        ]
        for operator, actual, expected_value, expected_result in cases:
            achievement = Achievement(
                "a1", "A1", "D1", [{"stat": "x", "operator": operator, "value": expected_value}]
            )
            with self.subTest(operator=operator, actual=actual, value=expected_value):
                self.assertEqual(
                    self.manager.check_requirement(achievement, {"x": actual}),
                    expected_result,
                )


class TestAchievementManagerUnlocking(unittest.TestCase):
    def setUp(self):
        self.manager = AchievementManager(achievements=[])
        self.manager.add_achievement(
            Achievement("a1", "A1", "D1", [{"stat": "x", "operator": ">=", "value": 1}])
        )

    def test_unlock_achievement_by_id(self):
        result = self.manager.unlock_achievement("a1")
        self.assertTrue(result)
        self.assertTrue(self.manager.get_achievement("a1").unlocked)

    def test_unlock_unknown_id_returns_false(self):
        self.assertFalse(self.manager.unlock_achievement("missing"))

    def test_unlock_already_unlocked_returns_false_and_is_safe(self):
        self.manager.unlock_achievement("a1")
        first_ts = self.manager.get_achievement("a1").unlocked_at

        result = self.manager.unlock_achievement("a1")

        self.assertFalse(result)
        self.assertEqual(self.manager.get_achievement("a1").unlocked_at, first_ts)

    def test_cannot_unlock_same_achievement_multiple_times_via_check(self):
        stats = {"x": 5}
        first = self.manager.check_achievements(stats)
        second = self.manager.check_achievements(stats)

        self.assertEqual([a.achievement_id for a in first], ["a1"])
        self.assertEqual(second, [])
        self.assertEqual(
            len(self.manager.get_unlocked_achievements()), 1
        )


class TestAchievementManagerCheckAchievements(unittest.TestCase):
    def setUp(self):
        self.manager = AchievementManager(achievements=[])
        self.manager.add_achievement(
            Achievement("a1", "A1", "D1", [{"stat": "x", "operator": ">=", "value": 1}])
        )
        self.manager.add_achievement(
            Achievement("a2", "A2", "D2", [{"stat": "y", "operator": "==", "value": True}])
        )
        self.manager.add_achievement(
            Achievement("a3", "A3", "D3", [{"stat": "z", "operator": ">=", "value": 100}])
        )

    def test_check_achievements_unlocks_all_matching(self):
        newly_unlocked = self.manager.check_achievements({"x": 5, "y": True, "z": 1})
        ids = sorted(a.achievement_id for a in newly_unlocked)
        self.assertEqual(ids, ["a1", "a2"])

    def test_check_achievements_returns_empty_when_nothing_matches(self):
        newly_unlocked = self.manager.check_achievements({"x": 0, "y": False, "z": 1})
        self.assertEqual(newly_unlocked, [])

    def test_check_achievements_skips_already_unlocked(self):
        self.manager.check_achievements({"x": 5, "y": True, "z": 1})
        second_pass = self.manager.check_achievements({"x": 5, "y": True, "z": 200})
        ids = [a.achievement_id for a in second_pass]
        self.assertEqual(ids, ["a3"])

    def test_check_achievements_handles_missing_stats_dict(self):
        # No stats at all -- should not raise, nothing unlocks.
        self.assertEqual(self.manager.check_achievements(), [])
        self.assertEqual(self.manager.check_achievements(None), [])

    def test_check_achievements_handles_partial_stats(self):
        # Only some stats present; achievements needing missing stats
        # simply stay locked, no exception.
        newly_unlocked = self.manager.check_achievements({"x": 5})
        self.assertEqual([a.achievement_id for a in newly_unlocked], ["a1"])


class TestAchievementManagerQueries(unittest.TestCase):
    def setUp(self):
        self.manager = AchievementManager(achievements=[])
        self.manager.add_achievement(Achievement("a1", "A1", "D1", []))
        self.manager.add_achievement(Achievement("a2", "A2", "D2", []))

    def test_get_locked_achievements_initially_all(self):
        self.assertEqual(len(self.manager.get_locked_achievements()), 2)
        self.assertEqual(len(self.manager.get_unlocked_achievements()), 0)

    def test_get_unlocked_after_unlock(self):
        self.manager.unlock_achievement("a1")
        unlocked = self.manager.get_unlocked_achievements()
        locked = self.manager.get_locked_achievements()

        self.assertEqual([a.achievement_id for a in unlocked], ["a1"])
        self.assertEqual([a.achievement_id for a in locked], ["a2"])

    def test_get_progress_empty_manager(self):
        empty_manager = AchievementManager(achievements=[])
        progress = empty_manager.get_progress()
        self.assertEqual(progress["total_count"], 0)
        self.assertEqual(progress["unlocked_count"], 0)
        self.assertEqual(progress["completion_percent"], 0.0)

    def test_get_progress_partial(self):
        self.manager.unlock_achievement("a1")
        progress = self.manager.get_progress()

        self.assertEqual(progress["unlocked_count"], 1)
        self.assertEqual(progress["total_count"], 2)
        self.assertEqual(progress["completion_percent"], 50.0)
        self.assertEqual(progress["unlocked_ids"], ["a1"])

    def test_get_progress_full(self):
        self.manager.unlock_achievement("a1")
        self.manager.unlock_achievement("a2")
        progress = self.manager.get_progress()
        self.assertEqual(progress["completion_percent"], 100.0)


class TestAchievementManagerReset(unittest.TestCase):
    def test_reset_locks_all_achievements(self):
        manager = AchievementManager()
        manager.check_achievements({"cases_solved": 1, "solved": True})
        self.assertGreater(len(manager.get_unlocked_achievements()), 0)

        manager.reset()

        self.assertEqual(len(manager.get_unlocked_achievements()), 0)
        self.assertTrue(all(a.unlocked_at is None for a in manager.get_all_achievements()))


class TestAchievementManagerSerialization(unittest.TestCase):
    def test_to_dict_from_dict_round_trip(self):
        manager = AchievementManager(achievements=[])
        manager.add_achievement(Achievement("a1", "A1", "D1", []))
        manager.add_achievement(Achievement("a2", "A2", "D2", []))
        manager.unlock_achievement("a1")

        rebuilt = AchievementManager.from_dict(manager.to_dict())

        self.assertEqual(len(rebuilt.get_all_achievements()), 2)
        self.assertTrue(rebuilt.get_achievement("a1").unlocked)
        self.assertFalse(rebuilt.get_achievement("a2").unlocked)
        self.assertEqual(
            rebuilt.get_achievement("a1").unlocked_at,
            manager.get_achievement("a1").unlocked_at,
        )

    def test_from_dict_none_falls_back_to_defaults(self):
        manager = AchievementManager.from_dict(None)
        self.assertEqual(len(manager.get_all_achievements()), 8)

    def test_from_dict_empty_dict_falls_back_to_defaults(self):
        manager = AchievementManager.from_dict({})
        self.assertEqual(len(manager.get_all_achievements()), 8)

    def test_from_dict_malformed_achievements_falls_back_to_defaults(self):
        manager = AchievementManager.from_dict({"achievements": "not a list"})
        self.assertEqual(len(manager.get_all_achievements()), 8)

    def test_from_dict_skips_invalid_entries_but_keeps_valid_ones(self):
        data = {
            "achievements": [
                {"achievement_id": "ok", "name": "OK", "description": "Fine"},
                {"achievement_id": "bad"},  # missing required fields
                "not even a dict",
            ]
        }
        manager = AchievementManager.from_dict(data)
        self.assertEqual(len(manager.get_all_achievements()), 1)
        self.assertIsNotNone(manager.get_achievement("ok"))


# ---------------------------------------------------------------------------
# GameController integration
# ---------------------------------------------------------------------------


class TestGameControllerAchievementIntegration(unittest.TestCase):
    def setUp(self):
        self.saves_dir = tempfile.mkdtemp()
        self.controller = GameController("p1", "Ada Detective", saves_dir=self.saves_dir)
        self.controller.load_case("case_001")
        self.controller.start_investigation()

    def _all_evidence_ids(self):
        return list(self.controller.case.evidence)

    def _all_clue_ids(self):
        return list(self.controller.case.clues)

    def test_has_achievement_manager(self):
        self.assertIsNotNone(self.controller.achievement_manager)
        self.assertEqual(len(self.controller.get_achievements()), 8)

    def test_discover_evidence_triggers_achievement_check(self):
        for evidence_id in self._all_evidence_ids():
            self.controller.discover_evidence(evidence_id)

        unlocked_ids = {a.achievement_id for a in self.controller.get_unlocked_achievements()}
        self.assertIn("evidence_hunter", unlocked_ids)

    def test_discover_evidence_partial_does_not_unlock_evidence_hunter(self):
        evidence_ids = self._all_evidence_ids()
        self.assertGreater(len(evidence_ids), 1)
        self.controller.discover_evidence(evidence_ids[0])

        unlocked_ids = {a.achievement_id for a in self.controller.get_unlocked_achievements()}
        self.assertNotIn("evidence_hunter", unlocked_ids)

    def test_discover_clue_triggers_achievement_check(self):
        for clue_id in self._all_clue_ids():
            self.controller.discover_clue(clue_id)

        unlocked_ids = {a.achievement_id for a in self.controller.get_unlocked_achievements()}
        self.assertIn("clue_collector", unlocked_ids)

    def test_conclude_case_triggers_achievement_check(self):
        outcome = self.controller.conclude_case(self.controller.case.correct_suspect)

        self.assertIn("achievements_unlocked", outcome)
        self.assertIn("first_case", outcome["achievements_unlocked"])
        unlocked_ids = {a.achievement_id for a in self.controller.get_unlocked_achievements()}
        self.assertIn("first_case", unlocked_ids)

    def test_conclude_case_wrong_suspect_does_not_unlock_first_case(self):
        wrong_suspect = next(
            s for s in self.controller.case.suspects
            if s != self.controller.case.correct_suspect
        )
        outcome = self.controller.conclude_case(wrong_suspect)

        self.assertFalse(outcome["solved"])
        unlocked_ids = {a.achievement_id for a in self.controller.get_unlocked_achievements()}
        self.assertNotIn("first_case", unlocked_ids)
        self.assertNotIn("master_investigator", unlocked_ids)

    def test_full_perfect_run_unlocks_perfect_investigation(self):
        for evidence_id in self._all_evidence_ids():
            self.controller.discover_evidence(evidence_id)
        for clue_id in self._all_clue_ids():
            self.controller.discover_clue(clue_id)

        outcome = self.controller.conclude_case(self.controller.case.correct_suspect)

        self.assertIn("perfect_investigation", outcome["achievements_unlocked"])

    def test_achievement_unlock_is_idempotent_across_multiple_events(self):
        for evidence_id in self._all_evidence_ids():
            self.controller.discover_evidence(evidence_id)

        first_ts = self.controller.achievement_manager.get_achievement(
            "evidence_hunter"
        ).unlocked_at

        # Trigger another check (e.g. via discover_clue) -- must not
        # re-unlock or change the timestamp of an already-unlocked
        # achievement.
        if self._all_clue_ids():
            self.controller.discover_clue(self._all_clue_ids()[0])

        second_ts = self.controller.achievement_manager.get_achievement(
            "evidence_hunter"
        ).unlocked_at

        self.assertEqual(first_ts, second_ts)
        unlocked = [
            a for a in self.controller.get_unlocked_achievements()
            if a.achievement_id == "evidence_hunter"
        ]
        self.assertEqual(len(unlocked), 1)

    def test_get_achievement_progress(self):
        progress = self.controller.get_achievement_progress()
        self.assertEqual(progress["total_count"], 8)
        self.assertEqual(progress["unlocked_count"], 0)

    def tearDown(self):
        import shutil

        shutil.rmtree(self.saves_dir, ignore_errors=True)


class TestGameControllerAchievementPersistence(unittest.TestCase):
    def setUp(self):
        self.saves_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.saves_dir, ignore_errors=True)

    def test_save_and_load_restores_unlocked_achievements_and_timestamps(self):
        controller = GameController("p1", "Ada", saves_dir=self.saves_dir)
        controller.load_case("case_001")
        controller.start_investigation()

        for evidence_id in controller.case.evidence:
            controller.discover_evidence(evidence_id)

        unlocked_before = {
            a.achievement_id: a.unlocked_at
            for a in controller.get_unlocked_achievements()
        }
        self.assertIn("evidence_hunter", unlocked_before)

        self.assertTrue(controller.save_game("slot_1"))

        reloaded = GameController("p1", "Ada", saves_dir=self.saves_dir)
        self.assertTrue(reloaded.load_game("slot_1"))

        unlocked_after = {
            a.achievement_id: a.unlocked_at
            for a in reloaded.get_unlocked_achievements()
        }
        self.assertEqual(unlocked_before, unlocked_after)

    def test_save_without_achievements_then_load_is_backward_compatible(self):
        controller = GameController("p1", "Ada", saves_dir=self.saves_dir)
        controller.load_case("case_001")
        controller.start_investigation()
        controller.discover_evidence(controller.case.evidence[0])

        save_manager = SaveManager(saves_dir=self.saves_dir, case_manager=controller.case_manager)
        ok = save_manager.save_game(
            controller.game_state,
            slot_name="legacy_slot",
            evidence_manager=controller.evidence_manager,
            clue_manager=controller.clue_manager,
            suspect_manager=controller.suspect_manager,
            investigation=controller.investigation,
            # No achievement_manager passed -- simulates a save
            # written before the achievement system existed.
        )
        self.assertTrue(ok)

        reloaded = GameController("p1", "Ada", saves_dir=self.saves_dir)
        self.assertTrue(reloaded.load_game("legacy_slot"))

        # Falls back to a fresh default achievement set, none unlocked.
        self.assertEqual(len(reloaded.get_achievements()), 8)
        self.assertEqual(reloaded.get_unlocked_achievements(), [])

    def test_load_achievement_state_missing_slot_returns_none(self):
        save_manager = SaveManager(saves_dir=self.saves_dir)
        self.assertIsNone(save_manager.load_achievement_state("does_not_exist"))

    def test_conclude_case_then_save_load_preserves_all_unlocks(self):
        controller = GameController("p1", "Ada", saves_dir=self.saves_dir)
        controller.load_case("case_001")
        controller.start_investigation()

        for evidence_id in controller.case.evidence:
            controller.discover_evidence(evidence_id)
        for clue_id in controller.case.clues:
            controller.discover_clue(clue_id)

        controller.conclude_case(controller.case.correct_suspect)
        unlocked_before = sorted(
            a.achievement_id for a in controller.get_unlocked_achievements()
        )
        self.assertGreater(len(unlocked_before), 0)

        controller.save_game("slot_2")

        reloaded = GameController("p1", "Ada", saves_dir=self.saves_dir)
        reloaded.load_game("slot_2")
        unlocked_after = sorted(
            a.achievement_id for a in reloaded.get_unlocked_achievements()
        )

        self.assertEqual(unlocked_before, unlocked_after)


if __name__ == "__main__":
    unittest.main()
