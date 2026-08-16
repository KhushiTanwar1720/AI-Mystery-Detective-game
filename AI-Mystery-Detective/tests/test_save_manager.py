"""
Unit and integration tests for SaveManager (game/save_manager.py).

Tests cover:
- Basic save/load round-trip of a GameState (score, accuracy, rank,
  discovered ids, interrogation history, hints, outcome).
- save_exists(), get_save_info(), list_saves(), delete_save().
- Full-context round-trip (evidence/clue discovered flags, suspect
  interrogation state, investigation progress) via the optional
  evidence_manager/clue_manager/suspect_manager/investigation
  arguments.
- Missing-save and corrupted-save handling.
- Invalid/unsupported save-version handling.
- Atomic-write behavior (no leftover temp file, no partial file on
  failure).
- End-to-end integration through GameController.save_game() /
  load_game(), using the real case_001 data, including resuming and
  completing a loaded investigation.

Run with:
    python -m unittest tests.test_save_manager
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.case import Case, CaseManager
from game.clue import Clue, ClueManager
from game.evidence import Evidence, EvidenceManager
from game.game_controller import GameController
from game.game_state import GameState
from game.investigation import Investigation
from game.player import Player
from game.save_manager import CURRENT_SAVE_VERSION, SaveManager
from game.suspect import Suspect, SuspectManager


# -- Shared fixtures ------------------------------------------------------

def make_case(**overrides) -> Case:
    defaults = dict(
        case_id="case_test",
        title="Test Case",
        description="A case used for testing.",
        location="Test Mansion",
        crime_type="theft",
        difficulty="easy",
        correct_suspect="suspect_a",
        # SuspectManager.get_suspects_for_case() (used by
        # SaveManager.save_game() to know which suspects belong to
        # the case) matches against Suspect.name, not suspect_id --
        # mirrors how the real case JSON files list suspects by name.
        suspects=["Colonel Mustard", "Professor Plum"],
        evidence=["evidence_a", "evidence_b"],
        clues=["clue_a"],
    )
    defaults.update(overrides)
    return Case(**defaults)


def make_evidence(**overrides) -> Evidence:
    defaults = dict(
        evidence_id="evidence_a",
        name="Bloody Glove",
        description="A glove with blood stains.",
        evidence_type="physical",
        location_found="Study",
        importance="high",
    )
    defaults.update(overrides)
    return Evidence(**defaults)


def make_clue(**overrides) -> Clue:
    defaults = dict(
        clue_id="clue_a",
        description="A faint smell of gunpowder.",
        source="Crime scene inspection",
        location="Study",
        importance="medium",
    )
    defaults.update(overrides)
    return Clue(**defaults)


def make_suspect(**overrides) -> Suspect:
    defaults = dict(
        suspect_id="suspect_a",
        name="Colonel Mustard",
        age=54,
        occupation="Retired officer",
        description="Gruff and impatient.",
        relationship_to_victim="Old friend",
    )
    defaults.update(overrides)
    return Suspect(**defaults)


def make_player(**overrides) -> Player:
    defaults = dict(player_id="player_1", name="Detective Rowan")
    defaults.update(overrides)
    return Player(**defaults)


class SaveManagerTestCase(unittest.TestCase):
    """Base class giving each test its own throwaway saves directory."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.saves_dir = Path(self._tmp.name)
        self.manager = SaveManager(saves_dir=self.saves_dir)

    def tearDown(self):
        self._tmp.cleanup()


# -- 1-4: Basic save / file creation / load / preserved state -------------

class TestBasicSaveAndLoad(SaveManagerTestCase):
    def setUp(self):
        super().setUp()
        self.player = make_player()
        self.case = make_case()
        self.state = GameState(player=self.player)
        self.state.start_case(self.case)
        self.state.add_discovered_evidence("evidence_a")
        self.state.add_discovered_clue("clue_a")
        self.state.hints_used = 2
        self.state.unnecessary_actions = 1
        self.state.update_score(score=150, accuracy=87.5, rank="Investigator")

    def test_save_valid_game_state_returns_true(self):
        self.assertTrue(self.manager.save_game(self.state, slot_name="slot_1"))

    def test_save_file_is_created(self):
        self.manager.save_game(self.state, slot_name="slot_1")
        expected_path = self.saves_dir / "slot_1.json"
        self.assertTrue(expected_path.exists())
        self.assertTrue(expected_path.is_file())

    def test_save_file_contains_expected_version_and_shape(self):
        self.manager.save_game(self.state, slot_name="slot_1")
        with open(self.saves_dir / "slot_1.json", "r", encoding="utf-8") as f:
            payload = json.load(f)
        self.assertEqual(payload["version"], CURRENT_SAVE_VERSION)
        self.assertIn("saved_at", payload)
        self.assertIn("game_state", payload)

    def test_load_returns_game_state_instance(self):
        self.manager.save_game(self.state, slot_name="slot_1")
        loaded = self.manager.load_game("slot_1")
        self.assertIsInstance(loaded, GameState)

    def test_load_preserves_case_id_and_status(self):
        self.manager.save_game(self.state, slot_name="slot_1")
        loaded = self.manager.load_game("slot_1")
        self.assertEqual(loaded.case.case_id, "case_test")
        self.assertEqual(loaded.status, "active")

    def test_load_preserves_score_accuracy_rank(self):
        self.manager.save_game(self.state, slot_name="slot_1")
        loaded = self.manager.load_game("slot_1")
        self.assertEqual(loaded.score, 150)
        self.assertAlmostEqual(loaded.accuracy, 87.5)
        self.assertEqual(loaded.rank, "Investigator")

    def test_load_preserves_hints_and_unnecessary_actions(self):
        self.manager.save_game(self.state, slot_name="slot_1")
        loaded = self.manager.load_game("slot_1")
        self.assertEqual(loaded.hints_used, 2)
        self.assertEqual(loaded.unnecessary_actions, 1)

    def test_load_preserves_discovered_evidence_and_clues(self):
        self.manager.save_game(self.state, slot_name="slot_1")
        loaded = self.manager.load_game("slot_1")
        self.assertEqual(loaded.discovered_evidence, ["evidence_a"])
        self.assertEqual(loaded.discovered_clues, ["clue_a"])

    def test_load_preserves_player_identity_and_progress(self):
        self.player.start_case("case_test")
        self.player.add_evidence("evidence_a")
        self.player.add_clue("clue_a")
        self.player.update_score(150)
        self.manager.save_game(self.state, slot_name="slot_1")
        loaded = self.manager.load_game("slot_1")

        self.assertEqual(loaded.player.player_id, "player_1")
        self.assertEqual(loaded.player.name, "Detective Rowan")
        self.assertEqual(loaded.player.current_case, "case_test")
        self.assertEqual(loaded.player.collected_evidence, ["evidence_a"])
        self.assertEqual(loaded.player.discovered_clues, ["clue_a"])
        self.assertEqual(loaded.player.investigation_score, 150)

    def test_load_preserves_interrogation_history(self):
        self.state.record_interrogation(
            {
                "suspect_id": "suspect_a",
                "questions_asked": 2,
                "contradictions": [],
            }
        )
        self.manager.save_game(self.state, slot_name="slot_1")
        loaded = self.manager.load_game("slot_1")
        self.assertEqual(len(loaded.interrogation_history), 1)
        self.assertEqual(loaded.interrogation_history[0]["suspect_id"], "suspect_a")

    def test_load_preserves_outcome_after_case_completed(self):
        self.state.end_case({"solved": True, "accused_suspect": "suspect_a"})
        self.manager.save_game(self.state, slot_name="slot_1")
        loaded = self.manager.load_game("slot_1")
        self.assertEqual(loaded.status, "completed")
        self.assertTrue(loaded.outcome["solved"])


# -- 7-8: Evidence / clue / suspect (interrogation) state preservation ----

class TestFullContextRoundTrip(SaveManagerTestCase):
    def setUp(self):
        super().setUp()
        self.case = make_case()
        self.evidence_manager = EvidenceManager()
        self.evidence_manager.add_evidence(make_evidence(evidence_id="evidence_a"))
        self.evidence_manager.add_evidence(make_evidence(evidence_id="evidence_b", name="Muddy Boots"))

        self.clue_manager = ClueManager()
        self.clue_manager.add_clue(make_clue(clue_id="clue_a"))

        self.suspect_manager = SuspectManager()
        self.suspect_manager.add_suspect(make_suspect(suspect_id="suspect_a"))
        self.suspect_manager.add_suspect(
            make_suspect(suspect_id="suspect_b", name="Professor Plum")
        )

        self.case_manager = CaseManager()
        self.case_manager.add_case(self.case)

        self.investigation = Investigation(
            case_manager=self.case_manager,
            evidence_manager=self.evidence_manager,
            clue_manager=self.clue_manager,
            suspect_manager=self.suspect_manager,
            investigator="Tester",
        )
        self.investigation.start_investigation("case_test")
        self.investigation.inspect_location("Study")
        self.investigation.discover_evidence("evidence_a")
        self.investigation.discover_clue("clue_a")
        self.investigation.examine_suspect("suspect_a")

        # Give the suspect some interrogation-derived state to persist.
        suspect_a = self.suspect_manager.get_suspect("suspect_a")
        suspect_a.add_statement("I was in the library all night.")
        suspect_a.update_alibi("Reading in the library")
        suspect_a.update_suspicion_level(25)

        self.player = make_player()
        self.state = GameState(player=self.player)
        self.state.start_case(self.case, self.investigation)
        self.state.add_discovered_evidence("evidence_a")
        self.state.add_discovered_clue("clue_a")

    def _save(self):
        return self.manager.save_game(
            self.state,
            slot_name="slot_1",
            evidence_manager=self.evidence_manager,
            clue_manager=self.clue_manager,
            suspect_manager=self.suspect_manager,
            investigation=self.investigation,
        )

    def test_evidence_discovered_flags_round_trip(self):
        self.assertTrue(self._save())

        fresh_evidence_manager = EvidenceManager()
        fresh_evidence_manager.add_evidence(make_evidence(evidence_id="evidence_a"))
        fresh_evidence_manager.add_evidence(
            make_evidence(evidence_id="evidence_b", name="Muddy Boots")
        )

        self.manager.load_game("slot_1", evidence_manager=fresh_evidence_manager)

        self.assertTrue(fresh_evidence_manager.get_evidence("evidence_a").is_discovered())
        self.assertFalse(fresh_evidence_manager.get_evidence("evidence_b").is_discovered())

    def test_clue_discovered_flags_round_trip(self):
        self.assertTrue(self._save())

        fresh_clue_manager = ClueManager()
        fresh_clue_manager.add_clue(make_clue(clue_id="clue_a"))

        self.manager.load_game("slot_1", clue_manager=fresh_clue_manager)

        self.assertTrue(fresh_clue_manager.get_clue("clue_a").is_discovered())

    def test_suspect_interrogation_state_round_trip(self):
        self.assertTrue(self._save())

        fresh_suspect_manager = SuspectManager()
        fresh_suspect_manager.add_suspect(make_suspect(suspect_id="suspect_a"))
        fresh_suspect_manager.add_suspect(
            make_suspect(suspect_id="suspect_b", name="Professor Plum")
        )

        self.manager.load_game("slot_1", suspect_manager=fresh_suspect_manager)

        restored = fresh_suspect_manager.get_suspect("suspect_a")
        self.assertEqual(restored.get_statements(), ["I was in the library all night."])
        self.assertEqual(restored.alibi, "Reading in the library")
        self.assertEqual(restored.suspicion_level, 25)

    def test_investigation_progress_round_trip(self):
        self.assertTrue(self._save())
        inv_state = self.manager.load_investigation_state("slot_1")
        self.assertIsNotNone(inv_state)
        self.assertEqual(inv_state["visited_locations"], ["Study"])
        self.assertEqual(inv_state["examined_suspects"], ["suspect_a"])
        self.assertGreater(len(inv_state["history"]), 0)

    def test_investigation_state_restores_via_load_state(self):
        self.assertTrue(self._save())
        inv_state = self.manager.load_investigation_state("slot_1")

        rebuilt = Investigation(
            case_manager=self.case_manager,
            evidence_manager=self.evidence_manager,
            clue_manager=self.clue_manager,
            suspect_manager=self.suspect_manager,
            investigator="Tester",
        )
        rebuilt.load_state(
            self.case,
            status=inv_state["status"],
            visited_locations=inv_state["visited_locations"],
            examined_suspects=inv_state["examined_suspects"],
            history=inv_state["history"],
        )

        self.assertEqual(rebuilt.get_visited_locations(), ["Study"])
        self.assertEqual(rebuilt.get_examined_suspects(), ["suspect_a"])
        # Re-examining the same suspect should still be blocked, proving
        # the restored state is live, not just cosmetic.
        with self.assertRaises(RuntimeError):
            rebuilt.examine_suspect("suspect_a")

    def test_missing_optional_managers_does_not_break_basic_load(self):
        """save_game()/load_game() with no manager context still works
        (backward compatible with the original two-argument API)."""
        ok = self.manager.save_game(self.state, slot_name="slot_1")
        self.assertTrue(ok)
        loaded = self.manager.load_game("slot_1")
        self.assertIsInstance(loaded, GameState)
        self.assertEqual(loaded.case.case_id, "case_test")


# -- 9-12: Slot management -------------------------------------------------

class TestSlotManagement(SaveManagerTestCase):
    def setUp(self):
        super().setUp()
        self.state = GameState(player=make_player())
        self.state.start_case(make_case())
        self.state.update_score(score=42, accuracy=60.0, rank="Detective Rookie")

    def test_save_exists_false_when_absent(self):
        self.assertFalse(self.manager.save_exists("slot_1"))

    def test_save_exists_true_after_saving(self):
        self.manager.save_game(self.state, slot_name="slot_1")
        self.assertTrue(self.manager.save_exists("slot_1"))

    def test_get_save_info_returns_none_when_absent(self):
        self.assertIsNone(self.manager.get_save_info("slot_1"))

    def test_get_save_info_returns_summary(self):
        self.manager.save_game(self.state, slot_name="slot_1")
        info = self.manager.get_save_info("slot_1")
        self.assertIsNotNone(info)
        self.assertEqual(info["slot_name"], "slot_1")
        self.assertEqual(info["case_id"], "case_test")
        self.assertEqual(info["score"], 42)
        self.assertEqual(info["rank"], "Detective Rookie")
        self.assertEqual(info["player_name"], "Detective Rowan")

    def test_list_saves_empty_initially(self):
        self.assertEqual(self.manager.list_saves(), [])

    def test_list_saves_returns_all_slots(self):
        self.manager.save_game(self.state, slot_name="slot_1")
        self.manager.save_game(self.state, slot_name="slot_2")
        saves = self.manager.list_saves()
        slot_names = sorted(s["slot_name"] for s in saves)
        self.assertEqual(slot_names, ["slot_1", "slot_2"])

    def test_delete_save_removes_existing_file(self):
        self.manager.save_game(self.state, slot_name="slot_1")
        self.assertTrue(self.manager.delete_save("slot_1"))
        self.assertFalse(self.manager.save_exists("slot_1"))

    def test_delete_save_returns_false_when_absent(self):
        self.assertFalse(self.manager.delete_save("slot_1"))

    def test_load_missing_save_returns_none(self):
        self.assertIsNone(self.manager.load_game("does_not_exist"))


# -- 13-16: Error handling & atomic writes ---------------------------------

class TestErrorHandling(SaveManagerTestCase):
    def test_load_corrupted_json_returns_none(self):
        bad_path = self.saves_dir / "corrupt.json"
        bad_path.write_text("{ this is not valid json ][", encoding="utf-8")
        self.assertIsNone(self.manager.load_game("corrupt"))

    def test_load_non_dict_json_returns_none(self):
        bad_path = self.saves_dir / "listy.json"
        bad_path.write_text("[1, 2, 3]", encoding="utf-8")
        self.assertIsNone(self.manager.load_game("listy"))

    def test_load_missing_required_keys_returns_none(self):
        bad_path = self.saves_dir / "incomplete.json"
        bad_path.write_text(json.dumps({"version": 1}), encoding="utf-8")
        self.assertIsNone(self.manager.load_game("incomplete"))

    def test_get_save_info_on_corrupted_file_returns_none(self):
        bad_path = self.saves_dir / "corrupt.json"
        bad_path.write_text("not json at all", encoding="utf-8")
        self.assertIsNone(self.manager.get_save_info("corrupt"))

    def test_save_none_game_state_returns_false(self):
        self.assertFalse(self.manager.save_game(None, slot_name="slot_1"))

    def test_save_invalid_object_returns_false(self):
        self.assertFalse(self.manager.save_game(object(), slot_name="slot_1"))

    def test_load_future_version_rejected(self):
        future_path = self.saves_dir / "future.json"
        future_path.write_text(
            json.dumps(
                {
                    "version": CURRENT_SAVE_VERSION + 1,
                    "saved_at": "2099-01-01T00:00:00+00:00",
                    "slot_name": "future",
                    "game_state": {"player_id": "p1", "case_id": "case_test"},
                }
            ),
            encoding="utf-8",
        )
        self.assertIsNone(self.manager.load_game("future"))

    def test_load_non_integer_version_rejected(self):
        bad_path = self.saves_dir / "badversion.json"
        bad_path.write_text(
            json.dumps(
                {
                    "version": "not-a-number",
                    "saved_at": "2099-01-01T00:00:00+00:00",
                    "slot_name": "badversion",
                    "game_state": {"player_id": "p1", "case_id": "case_test"},
                }
            ),
            encoding="utf-8",
        )
        self.assertIsNone(self.manager.load_game("badversion"))

    def test_slot_name_sanitized_no_path_traversal(self):
        state = GameState(player=make_player())
        state.start_case(make_case())
        self.manager.save_game(state, slot_name="../../evil")
        # Sanitization strips non-alphanumeric separators, so the file
        # should land inside saves_dir, never above it.
        for path in self.saves_dir.glob("*.json"):
            self.assertTrue(str(path.resolve()).startswith(str(self.saves_dir.resolve())))

    def test_no_leftover_temp_file_after_successful_save(self):
        state = GameState(player=make_player())
        state.start_case(make_case())
        self.manager.save_game(state, slot_name="slot_1")
        temp_files = list(self.saves_dir.glob("*.tmp"))
        self.assertEqual(temp_files, [])

    def test_save_file_is_valid_json_after_write(self):
        """Guards against partial/corrupted writes: the file on disk
        must always be fully valid JSON once save_game() returns True."""
        state = GameState(player=make_player())
        state.start_case(make_case())
        self.assertTrue(self.manager.save_game(state, slot_name="slot_1"))
        with open(self.saves_dir / "slot_1.json", "r", encoding="utf-8") as f:
            data = json.load(f)  # would raise if the write were partial
        self.assertIn("game_state", data)


# -- GameController integration --------------------------------------------

class TestGameControllerSaveLoad(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.saves_dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _play_up_to_interrogation(self, controller):
        controller.load_case("case_001")
        controller.start_investigation()

        discovered_evidence = []
        discovered_clues = []
        for loc in controller.get_case_locations():
            info = controller.explore_location(loc)
            for item in info["evidence_here"]:
                if not item["discovered"]:
                    controller.discover_evidence(item["evidence_id"])
                    discovered_evidence.append(item["evidence_id"])
            for item in info["clues_here"]:
                if not item["discovered"]:
                    controller.discover_clue(item["clue_id"])
                    discovered_clues.append(item["clue_id"])

        suspects = controller.get_case_suspects()
        target = suspects[0]
        controller.examine_suspect(target.suspect_id)
        controller.start_interrogation(target.suspect_id)
        q = controller.ask_question("Where were you?", category="alibi")
        controller.record_answer(q.question_id, target.alibi)
        controller.end_interrogation()

        return target, discovered_evidence, discovered_clues

    def test_save_game_requires_loaded_case(self):
        controller = GameController(player_id="p1", player_name="Detective", saves_dir=self.saves_dir)
        self.assertFalse(controller.save_game("slot_1"))

    def test_save_game_creates_slot(self):
        controller = GameController(player_id="p1", player_name="Detective", saves_dir=self.saves_dir)
        self._play_up_to_interrogation(controller)
        self.assertTrue(controller.save_game("slot_1"))
        self.assertTrue(controller.has_save("slot_1"))

    def test_load_game_restores_progress_into_fresh_controller(self):
        c1 = GameController(player_id="p1", player_name="Detective Rowan", saves_dir=self.saves_dir)
        target, discovered_evidence, discovered_clues = self._play_up_to_interrogation(c1)
        self.assertTrue(c1.save_game("slot_1"))

        c2 = GameController(player_id="unused", player_name="Unused", saves_dir=self.saves_dir)
        self.assertTrue(c2.load_game("slot_1"))

        self.assertEqual(c2.player.player_id, "p1")
        self.assertEqual(c2.player.name, "Detective Rowan")
        self.assertEqual(c2.case.case_id, "case_001")
        self.assertEqual(sorted(c2.game_state.discovered_evidence), sorted(discovered_evidence))
        self.assertEqual(sorted(c2.game_state.discovered_clues), sorted(discovered_clues))

        for eid in discovered_evidence:
            self.assertTrue(c2.evidence_manager.get_evidence(eid).is_discovered())
        for cid in discovered_clues:
            self.assertTrue(c2.clue_manager.get_clue(cid).is_discovered())

        self.assertIn(target.suspect_id, c2.investigation.get_examined_suspects())
        self.assertEqual(len(c2.game_state.interrogation_history), 1)

    def test_loaded_investigation_can_continue_and_conclude(self):
        c1 = GameController(player_id="p1", player_name="Detective Rowan", saves_dir=self.saves_dir)
        self._play_up_to_interrogation(c1)
        c1.save_game("slot_1")

        c2 = GameController(player_id="unused", player_name="Unused", saves_dir=self.saves_dir)
        c2.load_game("slot_1")

        # Play continues normally on the restored investigation/case.
        locations = c2.get_case_locations()
        info = c2.investigation.inspect_location(locations[0])
        self.assertIn("location", info)

        outcome = c2.conclude_case(c2.case.correct_suspect)
        self.assertTrue(outcome["solved"])
        self.assertIn("score_info", outcome)
        self.assertGreater(c2.player.investigation_score, 0)

    def test_load_game_returns_false_for_missing_slot(self):
        controller = GameController(player_id="p1", player_name="Detective", saves_dir=self.saves_dir)
        self.assertFalse(controller.load_game("nonexistent_slot"))

    def test_list_and_delete_save_via_controller(self):
        controller = GameController(player_id="p1", player_name="Detective", saves_dir=self.saves_dir)
        self._play_up_to_interrogation(controller)
        controller.save_game("slot_1")

        saves = controller.list_saves()
        self.assertEqual(len(saves), 1)
        self.assertEqual(saves[0]["slot_name"], "slot_1")

        self.assertTrue(controller.delete_save("slot_1"))
        self.assertFalse(controller.has_save("slot_1"))

    def test_completed_case_load_does_not_resume_live_investigation(self):
        c1 = GameController(player_id="p1", player_name="Detective Rowan", saves_dir=self.saves_dir)
        self._play_up_to_interrogation(c1)
        c1.run_ai_analysis()
        c1.conclude_case("Butler James")
        c1.save_game("slot_1")

        c2 = GameController(player_id="unused", player_name="Unused", saves_dir=self.saves_dir)
        self.assertTrue(c2.load_game("slot_1"))

        self.assertEqual(c2.case.status, "solved")
        self.assertIsNone(c2.investigation)
        self.assertEqual(c2.game_state.status, "completed")
        self.assertTrue(c2.game_state.outcome["solved"])


if __name__ == "__main__":
    unittest.main()
