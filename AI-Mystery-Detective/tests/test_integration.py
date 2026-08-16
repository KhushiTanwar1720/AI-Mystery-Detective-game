"""
Integration tests for AI Mystery Detective.

Unlike the other files under tests/, which unit-test each module in
isolation, this file exercises the connections between modules --
Case -> Investigation -> Evidence/Clue -> Suspect -> Interrogation ->
AI Analyzer -> Investigation Result -- via `game.game_controller.GameController`
and `game.app.App`, against the real sample data shipped in `cases/`.

Run with:
    python -m unittest tests.test_integration
"""

from __future__ import annotations

import io
import os
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.ai_analyzer import AnalysisResult
from game.app import App
from game.case import Case
from game.clue import Clue
from game.evidence import Evidence
from game.game_controller import GameController
from game.interrogation import Interrogation, Question, Statement
from game.investigation import Investigation
from game.suspect import Suspect


def make_controller() -> GameController:
    """Build a `GameController` pointed at the real project cases/ dir."""
    return GameController(player_id="p1", player_name="Test Detective")


class TestCaseToInvestigation(unittest.TestCase):
    """Case -> Investigation: loading a case wires it into an Investigation."""

    def test_load_case_returns_case(self) -> None:
        controller = make_controller()
        case = controller.load_case("case_001")
        self.assertIsInstance(case, Case)
        self.assertEqual(case.case_id, "case_001")

    def test_load_unknown_case_raises_key_error(self) -> None:
        controller = make_controller()
        with self.assertRaises(KeyError):
            controller.load_case("case_does_not_exist")

    def test_start_investigation_without_case_raises(self) -> None:
        controller = make_controller()
        with self.assertRaises(RuntimeError):
            controller.start_investigation()

    def test_start_investigation_activates_case(self) -> None:
        controller = make_controller()
        investigation = controller.start_investigation("case_001")
        self.assertIsInstance(investigation, Investigation)
        self.assertEqual(investigation.status, "active")
        self.assertEqual(investigation.case.case_id, "case_001")
        # Case -> Player: starting the investigation also starts the
        # player's own case tracking.
        self.assertEqual(controller.player.current_case, "case_001")


class TestInvestigationToEvidenceClue(unittest.TestCase):
    """Investigation -> Evidence/Clue: case data actually links up."""

    def test_case_evidence_and_clues_are_populated_on_load(self) -> None:
        # Case JSON files ship with empty evidence/clues lists; loading
        # must link the per-case evidence/clue files into the Case so
        # Investigation has something discoverable.
        controller = make_controller()
        case = controller.load_case("case_001")
        self.assertGreater(len(case.evidence), 0)
        self.assertGreater(len(case.clues), 0)

    def test_discover_evidence_updates_investigation_and_player(self) -> None:
        controller = make_controller()
        controller.start_investigation("case_001")
        case = controller.case
        evidence_id = case.evidence[0]

        evidence = controller.discover_evidence(evidence_id)

        self.assertIsInstance(evidence, Evidence)
        self.assertTrue(evidence.is_discovered())
        self.assertIn(evidence_id, controller.player.collected_evidence)

    def test_discover_clue_updates_investigation_and_player(self) -> None:
        controller = make_controller()
        controller.start_investigation("case_001")
        case = controller.case
        clue_id = case.clues[0]

        clue = controller.discover_clue(clue_id)

        self.assertIsInstance(clue, Clue)
        self.assertTrue(clue.is_discovered())
        self.assertIn(clue_id, controller.player.discovered_clues)

    def test_explore_location_surfaces_evidence_and_clues(self) -> None:
        controller = make_controller()
        controller.start_investigation("case_001")
        locations = controller.get_case_locations()
        self.assertTrue(locations)

        found_evidence_or_clue = False
        for location in locations:
            info = controller.explore_location(location)
            if info["evidence_here"] or info["clues_here"]:
                found_evidence_or_clue = True
        self.assertTrue(found_evidence_or_clue)


class TestInvestigationToSuspect(unittest.TestCase):
    """Investigation -> Suspect: suspects load and can be examined."""

    def test_get_case_suspects_returns_case_suspects(self) -> None:
        controller = make_controller()
        controller.load_case("case_001")
        suspects = controller.get_case_suspects()
        self.assertEqual(len(suspects), 3)
        names = {s.name for s in suspects}
        self.assertIn("Butler James", names)

    def test_examine_suspect_via_controller(self) -> None:
        controller = make_controller()
        controller.start_investigation("case_001")
        suspects = controller.get_case_suspects()
        suspect = controller.examine_suspect(suspects[0].suspect_id)
        self.assertIsInstance(suspect, Suspect)
        self.assertIn(suspects[0].suspect_id, controller.investigation._examined_suspects)


class TestSuspectToInterrogation(unittest.TestCase):
    """Suspect -> Interrogation: interrogating a suspect updates their profile."""

    def test_start_interrogation_selects_suspect(self) -> None:
        controller = make_controller()
        controller.start_investigation("case_001")
        suspects = controller.get_case_suspects()
        target = suspects[0]

        interrogation = controller.start_interrogation(target.suspect_id)

        self.assertIsInstance(interrogation, Interrogation)
        self.assertEqual(interrogation.suspect.suspect_id, target.suspect_id)
        # Same SuspectManager instance is shared with the Investigation.
        self.assertIs(interrogation.suspect_manager, controller.suspect_manager)

    def test_ask_and_answer_updates_suspect_statements(self) -> None:
        controller = make_controller()
        controller.start_investigation("case_001")
        suspects = controller.get_case_suspects()
        target = suspects[0]
        before_count = len(target.get_statements())

        controller.start_interrogation(target.suspect_id)
        question = controller.ask_question("Where were you?", category="alibi")
        self.assertIsInstance(question, Question)
        statement = controller.record_answer(question.question_id, "In the kitchen.")
        self.assertIsInstance(statement, Statement)

        self.assertEqual(len(target.get_statements()), before_count + 1)
        self.assertIn("In the kitchen.", target.get_statements())

    def test_end_interrogation_without_start_raises(self) -> None:
        controller = make_controller()
        controller.start_investigation("case_001")
        with self.assertRaises(RuntimeError):
            controller.end_interrogation()


class TestToAIAnalyzer(unittest.TestCase):
    """Investigation/Interrogation -> AI Analyzer: data actually reaches it."""

    def test_run_ai_analysis_without_case_raises(self) -> None:
        controller = make_controller()
        with self.assertRaises(RuntimeError):
            controller.run_ai_analysis()

    def test_run_ai_analysis_reflects_discovered_data(self) -> None:
        controller = make_controller()
        controller.start_investigation("case_001")
        case = controller.case
        for evidence_id in list(case.evidence):
            controller.discover_evidence(evidence_id)
        for clue_id in list(case.clues):
            controller.discover_clue(clue_id)

        suspects = controller.get_case_suspects()
        target = suspects[0]
        controller.start_interrogation(target.suspect_id)
        question = controller.ask_question("Where were you?", category="alibi")
        controller.record_answer(question.question_id, target.alibi)
        controller.end_interrogation()

        result = controller.run_ai_analysis()

        self.assertIsInstance(result, AnalysisResult)
        self.assertTrue(result.success)
        self.assertEqual(
            result.data["progress"]["evidence_discovered"], len(case.evidence)
        )
        self.assertEqual(result.data["progress"]["clues_discovered"], len(case.clues))
        # Never leak the solution to the analyzer's view of the case.
        self.assertNotIn("correct_suspect", result.data["case"])
        scores = result.data["suspicion_scores"]["data"]["scores"]
        self.assertEqual(len(scores), len(suspects))

    def test_ai_analyzer_never_receives_solution(self) -> None:
        controller = make_controller()
        controller.start_investigation("case_001")
        controller.run_ai_analysis()
        self.assertNotIn("correct_suspect", controller.ai_analyzer.case_info)


class TestFullGameFlow(unittest.TestCase):
    """End-to-end: Case -> Player -> Investigation -> Evidence/Clues ->
    Suspects -> Interrogation -> AI Analyzer -> Investigation Result.
    """

    def test_full_flow_via_game_controller(self) -> None:
        controller = make_controller()

        case = controller.load_case("case_001")
        controller.start_investigation()

        for location in controller.get_case_locations():
            info = controller.explore_location(location)
            for evidence_info in info["evidence_here"]:
                if not evidence_info["discovered"]:
                    controller.discover_evidence(evidence_info["evidence_id"])
            for clue_info in info["clues_here"]:
                if not clue_info["discovered"]:
                    controller.discover_clue(clue_info["clue_id"])

        suspects = controller.get_case_suspects()
        for suspect in suspects:
            controller.examine_suspect(suspect.suspect_id)

        target = suspects[0]
        controller.start_interrogation(target.suspect_id)
        question = controller.ask_question("Where were you?", category="alibi")
        controller.record_answer(question.question_id, target.alibi)
        controller.end_interrogation()

        analysis = controller.run_ai_analysis()
        top_suspect = analysis.data["suspicion_scores"]["data"]["scores"][0]["name"]

        outcome = controller.conclude_case(top_suspect)

        self.assertIn(outcome["case_status"], ("solved", "failed"))
        self.assertEqual(case.status, outcome["case_status"])
        self.assertIsNone(controller.player.current_case)
        self.assertEqual(controller.player.cases_solved, 1)
        # The real sample data's top-suspicion suspect is the culprit.
        self.assertTrue(outcome["solved"])
        self.assertGreater(controller.player.investigation_score, 0)

    def test_full_flow_via_app_runs_without_error(self) -> None:
        app = App(player_id="p2", player_name="Integration Tester")
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            controller = app.start("case_001")

        output = buffer.getvalue()
        self.assertIn("Investigation summary generated", output)
        self.assertIn("Final accusation", output)
        self.assertFalse(app.running)
        self.assertEqual(controller.case.case_id, "case_001")
        self.assertEqual(controller.investigation.status, "ended")
        self.assertEqual(controller.player.cases_solved, 1)


if __name__ == "__main__":
    unittest.main()
