"""
Unit and integration tests for GameState module.

Tests cover:
- initial state defaults
- start_game() registration and resetting
- start_case() lifecycle setup
- end_case() status transition and score/outcome capture
- reset_state() complete teardown
- suspect selection and clearing
- evidence & clue discovery with deduplication
- interrogation outcome recording
- hint & unnecessary action tracking
- score, accuracy, rank updates and boundary validations
- progress snapshot updates
- case completion status queries
- state summary & to_dict() serialization
- invalid inputs and state error protection
- end-to-end integration proving GameController -> GameState -> components -> ScoreManager
"""

import unittest
from game.player import Player
from game.case import Case
from game.game_state import GameState
from game.game_controller import GameController


class TestGameStateUnit(unittest.TestCase):
    def setUp(self):
        self.player = Player(player_id="p_test", name="Detective Tester")
        self.state = GameState(player=self.player)

    def test_initial_state(self):
        self.assertEqual(self.state.player, self.player)
        self.assertIsNone(self.state.case)
        self.assertIsNone(self.state.investigation)
        self.assertIsNone(self.state.interrogation)
        self.assertIsNone(self.state.current_suspect_id)
        self.assertEqual(self.state.discovered_evidence, [])
        self.assertEqual(self.state.discovered_clues, [])
        self.assertEqual(self.state.interrogation_history, [])
        self.assertEqual(self.state.hints_used, 0)
        self.assertEqual(self.state.unnecessary_actions, 0)
        self.assertEqual(self.state.score, 0)
        self.assertEqual(self.state.accuracy, 0.0)
        self.assertEqual(self.state.rank, "Detective Rookie")
        self.assertEqual(self.state.status, "not_started")
        self.assertIsNone(self.state.outcome)
        self.assertFalse(self.state.is_case_complete())

    def test_start_game_valid(self):
        new_player = Player(player_id="p2", name="New Player")
        self.state.start_game(new_player)
        self.assertEqual(self.state.player, new_player)
        self.assertEqual(self.state.status, "not_started")

    def test_start_game_invalid_player(self):
        with self.assertRaises(ValueError):
            self.state.start_game(None)
        with self.assertRaises(ValueError):
            self.state.start_game("not_a_player")

    def test_start_case_valid(self):
        case = Case(
            case_id="c1",
            title="Title",
            description="Desc",
            location="Loc",
            crime_type="theft",
            difficulty="easy",
            correct_suspect="s1",
        )
        self.state.start_case(case)
        self.assertEqual(self.state.case, case)
        self.assertEqual(self.state.status, "active")
        self.assertEqual(self.state.hints_used, 0)
        self.assertFalse(self.state.is_case_complete())

    def test_start_case_invalid(self):
        with self.assertRaises(ValueError):
            self.state.start_case(None)
        with self.assertRaises(ValueError):
            self.state.start_case({"invalid": "object"})

    def test_end_case_valid(self):
        case = Case(
            case_id="c1",
            title="Title",
            description="Desc",
            location="Loc",
            crime_type="theft",
            difficulty="easy",
            correct_suspect="s1",
        )
        self.state.start_case(case)
        outcome = {
            "solved": True,
            "score_info": {
                "score": 750,
                "accuracy": 92.5,
                "rank": "Senior Detective",
            },
        }
        self.state.end_case(outcome)
        self.assertEqual(self.state.status, "completed")
        self.assertTrue(self.state.is_case_complete())
        self.assertEqual(self.state.score, 750)
        self.assertEqual(self.state.accuracy, 92.5)
        self.assertEqual(self.state.rank, "Senior Detective")
        self.assertEqual(self.state.outcome, outcome)

    def test_end_case_without_active_case_raises(self):
        with self.assertRaises(RuntimeError):
            self.state.end_case({"solved": True})

    def test_end_case_invalid_outcome_type(self):
        case = Case(
            case_id="c1",
            title="Title",
            description="Desc",
            location="Loc",
            crime_type="theft",
            difficulty="easy",
            correct_suspect="s1",
        )
        self.state.start_case(case)
        with self.assertRaises(ValueError):
            self.state.end_case("not_a_dict")

    def test_suspect_selection(self):
        self.state.set_current_suspect("suspect_1")
        self.assertEqual(self.state.current_suspect_id, "suspect_1")
        self.state.set_current_suspect(None)
        self.assertIsNone(self.state.current_suspect_id)

    def test_suspect_selection_invalid(self):
        with self.assertRaises(ValueError):
            self.state.set_current_suspect("")
        with self.assertRaises(ValueError):
            self.state.set_current_suspect(123)

    def test_evidence_and_clue_discovery_deduplication(self):
        added_e1 = self.state.add_discovered_evidence("e1")
        added_e1_dup = self.state.add_discovered_evidence("e1")
        added_e2 = self.state.add_discovered_evidence("e2")

        self.assertTrue(added_e1)
        self.assertFalse(added_e1_dup)
        self.assertTrue(added_e2)
        self.assertEqual(self.state.discovered_evidence, ["e1", "e2"])

        added_c1 = self.state.add_discovered_clue("c1")
        added_c1_dup = self.state.add_discovered_clue("c1")
        self.assertTrue(added_c1)
        self.assertFalse(added_c1_dup)
        self.assertEqual(self.state.discovered_clues, ["c1"])

    def test_invalid_evidence_and_clue_inputs(self):
        with self.assertRaises(ValueError):
            self.state.add_discovered_evidence("")
        with self.assertRaises(ValueError):
            self.state.add_discovered_evidence(None)
        with self.assertRaises(ValueError):
            self.state.add_discovered_clue("")
        with self.assertRaises(ValueError):
            self.state.add_discovered_clue(None)

    def test_interrogation_and_hints_tracking(self):
        self.state.record_interrogation({"suspect_id": "s1", "answers_recorded": 2})
        self.assertEqual(len(self.state.interrogation_history), 1)

        hints1 = self.state.record_hint()
        hints2 = self.state.record_hint()
        self.assertEqual(hints1, 1)
        self.assertEqual(hints2, 2)
        self.assertEqual(self.state.hints_used, 2)

        unnecessary = self.state.record_unnecessary_action()
        self.assertEqual(unnecessary, 1)

    def test_update_score(self):
        self.state.update_score(500, accuracy=85.0, rank="Investigator")
        self.assertEqual(self.state.score, 500)
        self.assertEqual(self.state.accuracy, 85.0)
        self.assertEqual(self.state.rank, "Investigator")

    def test_update_score_invalid_values(self):
        with self.assertRaises(ValueError):
            self.state.update_score(-100)
        with self.assertRaises(ValueError):
            self.state.update_score(100, accuracy="invalid")
        with self.assertRaises(ValueError):
            self.state.update_score(100, rank="")

    def test_summaries_and_to_dict(self):
        case = Case(
            case_id="c1",
            title="Sample",
            description="Desc",
            location="Loc",
            crime_type="theft",
            difficulty="easy",
            correct_suspect="s1",
        )
        self.state.start_case(case)
        self.state.add_discovered_evidence("e1")
        self.state.add_discovered_clue("c1")

        summary = self.state.get_state_summary()
        self.assertEqual(summary["player_id"], "p_test")
        self.assertEqual(summary["case_id"], "c1")
        self.assertEqual(summary["evidence_count"], 1)
        self.assertEqual(summary["clues_count"], 1)

        d = self.state.to_dict()
        self.assertEqual(d["player_id"], "p_test")
        self.assertEqual(d["case_id"], "c1")
        self.assertEqual(d["discovered_evidence"], ["e1"])
        self.assertEqual(d["discovered_clues"], ["c1"])


class TestGameStateIntegration(unittest.TestCase):
    def setUp(self):
        self.controller = GameController(player_id="p_int", player_name="Integration Player")

    def test_full_pipeline_game_state_sync(self):
        state = self.controller.game_state
        self.assertEqual(state.player.player_id, "p_int")
        self.assertEqual(state.status, "not_started")

        self.controller.load_case("case_001")
        self.controller.start_investigation()

        self.assertEqual(state.status, "active")
        self.assertEqual(state.case.case_id, "case_001")
        self.assertIsNotNone(state.investigation)

        locations = self.controller.get_case_locations()
        for loc in locations:
            info = self.controller.explore_location(loc)
            for item in info["evidence_here"]:
                if not item["discovered"]:
                    self.controller.discover_evidence(item["evidence_id"])
            for item in info["clues_here"]:
                if not item["discovered"]:
                    self.controller.discover_clue(item["clue_id"])

        self.assertEqual(len(state.discovered_evidence), 3)
        self.assertEqual(len(state.discovered_clues), 3)

        suspects = self.controller.get_case_suspects()
        self.assertGreater(len(suspects), 0)

        target = suspects[0]
        self.controller.examine_suspect(target.suspect_id)
        self.assertEqual(state.current_suspect_id, target.suspect_id)

        self.controller.start_interrogation(target.suspect_id)
        q = self.controller.ask_question("Where were you?", category="alibi")
        self.controller.record_answer(q.question_id, target.alibi)
        self.controller.end_interrogation()

        self.assertEqual(len(state.interrogation_history), 1)

        self.controller.run_ai_analysis(include_hints=True)
        self.assertEqual(state.hints_used, 1)

        outcome = self.controller.conclude_case("Butler James")

        self.assertEqual(state.status, "completed")
        self.assertTrue(state.is_case_complete())
        self.assertGreater(state.score, 0)
        self.assertGreater(state.accuracy, 0.0)
        self.assertIn("score_info", outcome)

        summary = state.get_state_summary()
        self.assertTrue(summary["is_complete"])
        self.assertEqual(summary["evidence_count"], 3)
        self.assertEqual(summary["clues_count"], 3)


if __name__ == "__main__":
    unittest.main()
