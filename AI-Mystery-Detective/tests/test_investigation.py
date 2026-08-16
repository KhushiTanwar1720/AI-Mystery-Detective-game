"""
Unit tests for the Investigation class (game/investigation.py).

Run with:
    python -m unittest tests.test_investigation
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.case import Case, CaseManager
from game.clue import Clue, ClueManager
from game.evidence import Evidence, EvidenceManager
from game.investigation import Investigation
from game.suspect import Suspect, SuspectManager


def make_case(**overrides) -> Case:
    """Helper to build a valid Case with sensible defaults."""
    defaults = dict(
        case_id="case_test",
        title="Test Case",
        description="A case used for testing.",
        location="Test Mansion",
        crime_type="theft",
        difficulty="easy",
        correct_suspect="suspect_a",
        suspects=["suspect_a", "suspect_b"],
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


def build_investigation(case: Case = None):
    """Build an Investigation wired up with a matching set of managers.

    Returns the investigation along with the underlying managers so
    tests can reach in and inspect/mutate state directly if needed.
    """
    case = case or make_case()

    case_manager = CaseManager()
    case_manager.add_case(case)

    evidence_manager = EvidenceManager()
    evidence_manager.add_evidence(make_evidence(evidence_id="evidence_a"))
    evidence_manager.add_evidence(
        make_evidence(
            evidence_id="evidence_b",
            name="Torn Letter",
            location_found="Garden",
        )
    )

    clue_manager = ClueManager()
    clue_manager.add_clue(make_clue(clue_id="clue_a"))

    suspect_manager = SuspectManager()
    suspect_manager.add_suspect(make_suspect(suspect_id="suspect_a"))
    suspect_manager.add_suspect(
        make_suspect(
            suspect_id="suspect_b",
            name="Professor Plum",
            occupation="Academic",
        )
    )

    investigation = Investigation(
        case_manager, evidence_manager, clue_manager, suspect_manager
    )
    return investigation, case_manager, evidence_manager, clue_manager, suspect_manager


class TestInvestigationCreation(unittest.TestCase):
    def test_valid_creation_defaults(self):
        investigation, *_ = build_investigation()
        self.assertEqual(investigation.status, "not_started")
        self.assertIsNone(investigation.case)
        self.assertEqual(investigation.investigator, "Player")
        self.assertEqual(investigation.get_history(), [])

    def test_invalid_investigator_raises(self):
        _, case_manager, evidence_manager, clue_manager, suspect_manager = (
            build_investigation()
        )
        with self.assertRaises(ValueError):
            Investigation(
                case_manager,
                evidence_manager,
                clue_manager,
                suspect_manager,
                investigator="   ",
            )


class TestCaseSelectionAndStart(unittest.TestCase):
    def test_select_case_success(self):
        investigation, *_ = build_investigation()
        case = investigation.select_case("case_test")
        self.assertIs(case, investigation.case)
        self.assertEqual(investigation.status, "not_started")

    def test_select_unknown_case_raises_key_error(self):
        investigation, *_ = build_investigation()
        with self.assertRaises(KeyError):
            investigation.select_case("does_not_exist")

    def test_select_case_invalid_id_raises(self):
        investigation, *_ = build_investigation()
        with self.assertRaises(ValueError):
            investigation.select_case("")

    def test_start_investigation_without_case_raises(self):
        investigation, *_ = build_investigation()
        with self.assertRaises(RuntimeError):
            investigation.start_investigation()

    def test_start_investigation_with_case_id(self):
        investigation, *_ = build_investigation()
        case = investigation.start_investigation("case_test")
        self.assertEqual(investigation.status, "active")
        self.assertEqual(case.get_status(), "in_progress")

    def test_start_investigation_twice_raises(self):
        investigation, *_ = build_investigation()
        investigation.start_investigation("case_test")
        with self.assertRaises(RuntimeError):
            investigation.start_investigation()

    def test_select_case_while_active_raises(self):
        investigation, case_manager, *_ = build_investigation()
        investigation.start_investigation("case_test")
        case_manager.add_case(make_case(case_id="case_other"))
        with self.assertRaises(RuntimeError):
            investigation.select_case("case_other")


class TestInspectLocation(unittest.TestCase):
    def test_inspect_location_requires_active_investigation(self):
        investigation, *_ = build_investigation()
        investigation.select_case("case_test")
        with self.assertRaises(RuntimeError):
            investigation.inspect_location("Study")

    def test_inspect_location_invalid_input_raises(self):
        investigation, *_ = build_investigation()
        investigation.start_investigation("case_test")
        with self.assertRaises(ValueError):
            investigation.inspect_location("")

    def test_inspect_location_first_visit_flag(self):
        investigation, *_ = build_investigation()
        investigation.start_investigation("case_test")

        first = investigation.inspect_location("Study")
        self.assertTrue(first["first_visit"])

        second = investigation.inspect_location("Study")
        self.assertFalse(second["first_visit"])

        self.assertEqual(investigation.get_visited_locations(), ["Study"])

    def test_inspect_location_surfaces_matching_evidence_and_clues(self):
        investigation, *_ = build_investigation()
        investigation.start_investigation("case_test")

        result = investigation.inspect_location("Study")
        evidence_ids = [e["evidence_id"] for e in result["evidence_here"]]
        clue_ids = [c["clue_id"] for c in result["clues_here"]]

        self.assertIn("evidence_a", evidence_ids)
        self.assertNotIn("evidence_b", evidence_ids)  # located in "Garden"
        self.assertIn("clue_a", clue_ids)

        # Before discovery, descriptions should be withheld.
        evidence_entry = result["evidence_here"][0]
        self.assertNotIn("description", evidence_entry)


class TestDiscoverEvidence(unittest.TestCase):
    def test_discover_evidence_success(self):
        investigation, *_ = build_investigation()
        investigation.start_investigation("case_test")

        evidence = investigation.discover_evidence("evidence_a")
        self.assertTrue(evidence.is_discovered())

    def test_discover_evidence_requires_active_investigation(self):
        investigation, *_ = build_investigation()
        investigation.select_case("case_test")
        with self.assertRaises(RuntimeError):
            investigation.discover_evidence("evidence_a")

    def test_discover_evidence_invalid_id_raises(self):
        investigation, *_ = build_investigation()
        investigation.start_investigation("case_test")
        with self.assertRaises(ValueError):
            investigation.discover_evidence("")

    def test_discover_evidence_not_in_case_raises_key_error(self):
        investigation, _, evidence_manager, *_ = build_investigation()
        evidence_manager.add_evidence(
            make_evidence(evidence_id="evidence_outside_case")
        )
        investigation.start_investigation("case_test")
        with self.assertRaises(KeyError):
            investigation.discover_evidence("evidence_outside_case")

    def test_discover_evidence_listed_but_not_registered_raises_key_error(self):
        # Evidence id is listed on the case but was never registered
        # with the EvidenceManager -- a data-consistency problem the
        # Investigation should surface rather than silently ignore.
        case = make_case(
            case_id="case_missing_evidence",
            evidence=["evidence_ghost"],
        )
        investigation, case_manager, *_ = build_investigation()
        case_manager.add_case(case)
        investigation.start_investigation("case_missing_evidence")
        with self.assertRaises(KeyError):
            investigation.discover_evidence("evidence_ghost")

    def test_discover_evidence_duplicate_raises(self):
        investigation, *_ = build_investigation()
        investigation.start_investigation("case_test")
        investigation.discover_evidence("evidence_a")
        with self.assertRaises(RuntimeError):
            investigation.discover_evidence("evidence_a")


class TestDiscoverClue(unittest.TestCase):
    def test_discover_clue_success(self):
        investigation, *_ = build_investigation()
        investigation.start_investigation("case_test")
        clue = investigation.discover_clue("clue_a")
        self.assertTrue(clue.is_discovered())

    def test_discover_clue_not_in_case_raises_key_error(self):
        investigation, _, _, clue_manager, _ = build_investigation()
        clue_manager.add_clue(make_clue(clue_id="clue_outside_case"))
        investigation.start_investigation("case_test")
        with self.assertRaises(KeyError):
            investigation.discover_clue("clue_outside_case")

    def test_discover_clue_duplicate_raises(self):
        investigation, *_ = build_investigation()
        investigation.start_investigation("case_test")
        investigation.discover_clue("clue_a")
        with self.assertRaises(RuntimeError):
            investigation.discover_clue("clue_a")

    def test_discover_clue_requires_active_investigation(self):
        investigation, *_ = build_investigation()
        with self.assertRaises(RuntimeError):
            investigation.discover_clue("clue_a")


class TestExamineSuspect(unittest.TestCase):
    def test_examine_suspect_success(self):
        investigation, *_ = build_investigation()
        investigation.start_investigation("case_test")
        suspect = investigation.examine_suspect("suspect_a")
        self.assertEqual(suspect.suspect_id, "suspect_a")

    def test_examine_suspect_not_in_case_raises_key_error(self):
        investigation, _, _, _, suspect_manager = build_investigation()
        suspect_manager.add_suspect(
            make_suspect(suspect_id="suspect_outsider", name="Mr. Green")
        )
        investigation.start_investigation("case_test")
        with self.assertRaises(KeyError):
            investigation.examine_suspect("suspect_outsider")

    def test_examine_suspect_duplicate_raises(self):
        investigation, *_ = build_investigation()
        investigation.start_investigation("case_test")
        investigation.examine_suspect("suspect_a")
        with self.assertRaises(RuntimeError):
            investigation.examine_suspect("suspect_a")

    def test_examine_unknown_suspect_raises_key_error(self):
        investigation, *_ = build_investigation()
        investigation.start_investigation("case_test")
        with self.assertRaises(KeyError):
            investigation.examine_suspect("suspect_ghost")


class TestReviewStatements(unittest.TestCase):
    def test_review_statements_returns_copy(self):
        investigation, _, _, _, suspect_manager = build_investigation()
        suspect = suspect_manager.get_suspect("suspect_a")
        suspect.add_statement("I was in the kitchen all night.")

        investigation.start_investigation("case_test")
        statements = investigation.review_statements("suspect_a")
        statements.append("mutated locally only")

        self.assertEqual(
            suspect.get_statements(), ["I was in the kitchen all night."]
        )

    def test_review_statements_can_be_called_repeatedly(self):
        investigation, *_ = build_investigation()
        investigation.start_investigation("case_test")
        investigation.review_statements("suspect_a")
        investigation.review_statements("suspect_a")  # should not raise

    def test_review_statements_requires_active_investigation(self):
        investigation, *_ = build_investigation()
        with self.assertRaises(RuntimeError):
            investigation.review_statements("suspect_a")


class TestProgressAndHistory(unittest.TestCase):
    def test_progress_before_case_selected(self):
        investigation, *_ = build_investigation()
        progress = investigation.get_progress()
        self.assertEqual(progress["status"], "not_started")
        self.assertIsNone(progress["case_id"])

    def test_progress_tracks_discoveries(self):
        investigation, *_ = build_investigation()
        investigation.start_investigation("case_test")

        investigation.discover_evidence("evidence_a")
        investigation.discover_clue("clue_a")
        investigation.examine_suspect("suspect_a")
        investigation.inspect_location("Study")

        progress = investigation.get_progress()
        self.assertEqual(progress["evidence_discovered"], 1)
        self.assertEqual(progress["evidence_total"], 2)
        self.assertEqual(progress["clues_discovered"], 1)
        self.assertEqual(progress["clues_total"], 1)
        self.assertEqual(progress["suspects_examined"], 1)
        self.assertEqual(progress["suspects_total"], 2)
        self.assertEqual(progress["locations_visited"], 1)
        self.assertGreater(progress["completion_percent"], 0)

    def test_history_records_actions_in_order(self):
        investigation, *_ = build_investigation()
        investigation.start_investigation("case_test")
        investigation.inspect_location("Study")
        investigation.discover_evidence("evidence_a")

        history = investigation.get_history()
        actions = [entry["action"] for entry in history]
        self.assertEqual(
            actions,
            [
                "select_case",
                "start_investigation",
                "inspect_location",
                "discover_evidence",
            ],
        )

    def test_get_history_returns_copy(self):
        investigation, *_ = build_investigation()
        investigation.start_investigation("case_test")
        history = investigation.get_history()
        history.append({"action": "fake", "timestamp": "x", "details": {}})
        self.assertEqual(len(investigation.get_history()), 2)


class TestEndInvestigation(unittest.TestCase):
    def test_end_investigation_requires_active(self):
        investigation, *_ = build_investigation()
        with self.assertRaises(RuntimeError):
            investigation.end_investigation()

    def test_end_investigation_without_accusation(self):
        investigation, *_ = build_investigation()
        investigation.start_investigation("case_test")
        outcome = investigation.end_investigation()

        self.assertFalse(outcome["solved"])
        self.assertEqual(outcome["case_status"], "in_progress")
        self.assertEqual(investigation.status, "ended")

    def test_end_investigation_with_correct_accusation(self):
        investigation, *_ = build_investigation()
        investigation.start_investigation("case_test")
        outcome = investigation.end_investigation(accused_suspect="suspect_a")

        self.assertTrue(outcome["solved"])
        self.assertEqual(outcome["case_status"], "solved")

    def test_end_investigation_with_incorrect_accusation(self):
        investigation, *_ = build_investigation()
        investigation.start_investigation("case_test")
        outcome = investigation.end_investigation(accused_suspect="suspect_b")

        self.assertFalse(outcome["solved"])
        self.assertEqual(outcome["case_status"], "failed")

    def test_actions_after_end_raise(self):
        investigation, *_ = build_investigation()
        investigation.start_investigation("case_test")
        investigation.end_investigation()

        with self.assertRaises(RuntimeError):
            investigation.discover_evidence("evidence_b")
        with self.assertRaises(RuntimeError):
            investigation.start_investigation()


if __name__ == "__main__":
    unittest.main()
