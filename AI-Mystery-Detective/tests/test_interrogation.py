"""
Unit tests for the Interrogation, Question, and Statement classes
(game/interrogation.py).

Run with:
    python -m unittest tests.test_interrogation
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.interrogation import Interrogation, Question, Statement
from game.suspect import Suspect, SuspectManager


def make_suspect(**overrides) -> Suspect:
    """Helper to build a valid Suspect with sensible defaults."""
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


def build_interrogation():
    """Build an Interrogation wired up with a SuspectManager.

    Returns the interrogation along with the manager so tests can
    reach in and add more suspects if needed.
    """
    suspect_manager = SuspectManager()
    suspect_manager.add_suspect(make_suspect())
    suspect_manager.add_suspect(make_suspect(suspect_id="suspect_b", name="Mrs. Peacock"))

    interrogation = Interrogation(suspect_manager)
    return interrogation, suspect_manager


class TestQuestion(unittest.TestCase):
    def test_valid_creation_defaults(self):
        question = Question(question_id="q1", text="Where were you?")
        self.assertEqual(question.category, "general")
        self.assertFalse(question.answered)

    def test_empty_text_raises(self):
        with self.assertRaises(ValueError):
            Question(question_id="q1", text="")

    def test_mark_answered(self):
        question = Question(question_id="q1", text="Where were you?")
        question.mark_answered()
        self.assertTrue(question.is_answered())

    def test_mark_answered_twice_raises(self):
        question = Question(question_id="q1", text="Where were you?")
        question.mark_answered()
        with self.assertRaises(RuntimeError):
            question.mark_answered()

    def test_get_info(self):
        question = Question(question_id="q1", text="Where were you?", category="alibi")
        info = question.get_info()
        self.assertEqual(
            info,
            {
                "question_id": "q1",
                "text": "Where were you?",
                "category": "alibi",
                "answered": False,
            },
        )


class TestStatement(unittest.TestCase):
    def test_valid_creation(self):
        statement = Statement(
            statement_id="s1",
            suspect_id="suspect_a",
            question_id="q1",
            question_text="Where were you?",
            answer="In the kitchen.",
        )
        self.assertEqual(statement.answer, "In the kitchen.")
        self.assertTrue(statement.timestamp)

    def test_empty_answer_raises(self):
        with self.assertRaises(ValueError):
            Statement(
                statement_id="s1",
                suspect_id="suspect_a",
                question_id="q1",
                question_text="Where were you?",
                answer="",
            )

    def test_get_info(self):
        statement = Statement(
            statement_id="s1",
            suspect_id="suspect_a",
            question_id="q1",
            question_text="Where were you?",
            answer="In the kitchen.",
            timestamp="2026-01-01T00:00:00+00:00",
        )
        self.assertEqual(
            statement.get_info(),
            {
                "statement_id": "s1",
                "suspect_id": "suspect_a",
                "question_id": "q1",
                "question_text": "Where were you?",
                "answer": "In the kitchen.",
                "timestamp": "2026-01-01T00:00:00+00:00",
            },
        )


class TestInterrogationCreation(unittest.TestCase):
    def test_valid_creation_defaults(self):
        interrogation, _ = build_interrogation()
        self.assertEqual(interrogation.status, "not_started")
        self.assertIsNone(interrogation.suspect)
        self.assertEqual(interrogation.interrogator, "Detective")
        self.assertEqual(interrogation.get_history(), [])

    def test_invalid_interrogator_raises(self):
        _, suspect_manager = build_interrogation()
        with self.assertRaises(ValueError):
            Interrogation(suspect_manager, interrogator="   ")


class TestSuspectSelectionAndStart(unittest.TestCase):
    def test_select_suspect_success(self):
        interrogation, _ = build_interrogation()
        suspect = interrogation.select_suspect("suspect_a")
        self.assertIs(suspect, interrogation.suspect)
        self.assertEqual(interrogation.status, "not_started")

    def test_select_unknown_suspect_raises_key_error(self):
        interrogation, _ = build_interrogation()
        with self.assertRaises(KeyError):
            interrogation.select_suspect("does_not_exist")

    def test_select_suspect_invalid_id_raises(self):
        interrogation, _ = build_interrogation()
        with self.assertRaises(ValueError):
            interrogation.select_suspect("")

    def test_start_interrogation_without_suspect_raises(self):
        interrogation, _ = build_interrogation()
        with self.assertRaises(RuntimeError):
            interrogation.start_interrogation()

    def test_start_interrogation_with_suspect_id(self):
        interrogation, _ = build_interrogation()
        suspect = interrogation.start_interrogation("suspect_a")
        self.assertEqual(interrogation.status, "active")
        self.assertEqual(suspect.suspect_id, "suspect_a")

    def test_start_interrogation_twice_raises(self):
        interrogation, _ = build_interrogation()
        interrogation.start_interrogation("suspect_a")
        with self.assertRaises(RuntimeError):
            interrogation.start_interrogation()

    def test_select_suspect_while_active_raises(self):
        interrogation, _ = build_interrogation()
        interrogation.start_interrogation("suspect_a")
        with self.assertRaises(RuntimeError):
            interrogation.select_suspect("suspect_b")

    def test_start_after_end_raises(self):
        interrogation, _ = build_interrogation()
        interrogation.start_interrogation("suspect_a")
        interrogation.end_interrogation()
        with self.assertRaises(RuntimeError):
            interrogation.start_interrogation()


class TestAskQuestion(unittest.TestCase):
    def test_ask_question_requires_active_interrogation(self):
        interrogation, _ = build_interrogation()
        interrogation.select_suspect("suspect_a")
        with self.assertRaises(RuntimeError):
            interrogation.ask_question("Where were you?")

    def test_ask_question_invalid_text_raises(self):
        interrogation, _ = build_interrogation()
        interrogation.start_interrogation("suspect_a")
        with self.assertRaises(ValueError):
            interrogation.ask_question("")

    def test_ask_question_returns_unanswered_question(self):
        interrogation, _ = build_interrogation()
        interrogation.start_interrogation("suspect_a")
        question = interrogation.ask_question("Where were you?", category="alibi")
        self.assertFalse(question.is_answered())
        self.assertEqual(question.category, "alibi")

    def test_ask_question_ids_are_unique_within_session(self):
        interrogation, _ = build_interrogation()
        interrogation.start_interrogation("suspect_a")
        q1 = interrogation.ask_question("Where were you?")
        q2 = interrogation.ask_question("Did you see anyone?")
        self.assertNotEqual(q1.question_id, q2.question_id)


class TestRecordAnswer(unittest.TestCase):
    def test_record_answer_success(self):
        interrogation, _ = build_interrogation()
        interrogation.start_interrogation("suspect_a")
        question = interrogation.ask_question("Where were you?")
        statement = interrogation.record_answer(
            question.question_id, "In the kitchen."
        )
        self.assertEqual(statement.answer, "In the kitchen.")
        self.assertTrue(question.is_answered())

    def test_record_answer_updates_suspect_statements(self):
        interrogation, suspect_manager = build_interrogation()
        interrogation.start_interrogation("suspect_a")
        question = interrogation.ask_question("Where were you?")
        interrogation.record_answer(question.question_id, "In the kitchen.")

        suspect = suspect_manager.get_suspect("suspect_a")
        self.assertIn("In the kitchen.", suspect.get_statements())

    def test_record_answer_requires_active_interrogation(self):
        interrogation, _ = build_interrogation()
        interrogation.select_suspect("suspect_a")
        with self.assertRaises(RuntimeError):
            interrogation.record_answer("q1", "In the kitchen.")

    def test_record_answer_invalid_input_raises(self):
        interrogation, _ = build_interrogation()
        interrogation.start_interrogation("suspect_a")
        question = interrogation.ask_question("Where were you?")
        with self.assertRaises(ValueError):
            interrogation.record_answer(question.question_id, "")

    def test_record_answer_unknown_question_raises_key_error(self):
        interrogation, _ = build_interrogation()
        interrogation.start_interrogation("suspect_a")
        with self.assertRaises(KeyError):
            interrogation.record_answer("q_ghost", "In the kitchen.")

    def test_record_answer_duplicate_raises(self):
        interrogation, _ = build_interrogation()
        interrogation.start_interrogation("suspect_a")
        question = interrogation.ask_question("Where were you?")
        interrogation.record_answer(question.question_id, "In the kitchen.")
        with self.assertRaises(RuntimeError):
            interrogation.record_answer(question.question_id, "In the garden.")


class TestCompareStatements(unittest.TestCase):
    def test_no_contradictions_when_answers_consistent(self):
        interrogation, _ = build_interrogation()
        interrogation.start_interrogation("suspect_a")
        q1 = interrogation.ask_question("Where were you?")
        interrogation.record_answer(q1.question_id, "In the kitchen.")

        q2 = interrogation.ask_question("Where were you?")
        interrogation.record_answer(q2.question_id, "In the kitchen.")

        contradictions = interrogation.compare_statements()
        self.assertEqual(contradictions, [])

    def test_detects_contradiction_on_reasked_question(self):
        interrogation, _ = build_interrogation()
        interrogation.start_interrogation("suspect_a")

        q1 = interrogation.ask_question("Where were you at 9pm?")
        interrogation.record_answer(q1.question_id, "In the kitchen.")

        q2 = interrogation.ask_question("Where were you at 9pm?")
        interrogation.record_answer(q2.question_id, "In the garden.")

        contradictions = interrogation.compare_statements()
        self.assertEqual(len(contradictions), 1)
        answers = {s["answer"] for s in contradictions[0]["statements"]}
        self.assertEqual(answers, {"In the kitchen.", "In the garden."})

    def test_compare_statements_case_insensitive_question_grouping(self):
        interrogation, _ = build_interrogation()
        interrogation.start_interrogation("suspect_a")

        q1 = interrogation.ask_question("Where were you?")
        interrogation.record_answer(q1.question_id, "Kitchen")

        q2 = interrogation.ask_question("where were you?")
        interrogation.record_answer(q2.question_id, "Garden")

        contradictions = interrogation.compare_statements()
        self.assertEqual(len(contradictions), 1)

    def test_compare_statements_with_no_statements_returns_empty(self):
        interrogation, _ = build_interrogation()
        interrogation.start_interrogation("suspect_a")
        self.assertEqual(interrogation.compare_statements(), [])


class TestHistory(unittest.TestCase):
    def test_history_records_actions_in_order(self):
        interrogation, _ = build_interrogation()
        interrogation.start_interrogation("suspect_a")
        question = interrogation.ask_question("Where were you?")
        interrogation.record_answer(question.question_id, "In the kitchen.")

        history = interrogation.get_history()
        actions = [entry["action"] for entry in history]
        self.assertEqual(
            actions,
            [
                "select_suspect",
                "start_interrogation",
                "ask_question",
                "record_answer",
            ],
        )

    def test_get_history_returns_copy(self):
        interrogation, _ = build_interrogation()
        interrogation.start_interrogation("suspect_a")
        history = interrogation.get_history()
        history.append({"action": "fake", "timestamp": "x", "details": {}})
        self.assertEqual(len(interrogation.get_history()), 2)

    def test_get_questions_and_statements(self):
        interrogation, _ = build_interrogation()
        interrogation.start_interrogation("suspect_a")
        question = interrogation.ask_question("Where were you?")
        interrogation.record_answer(question.question_id, "In the kitchen.")

        self.assertEqual(len(interrogation.get_questions()), 1)
        self.assertEqual(len(interrogation.get_statements()), 1)


class TestEndInterrogation(unittest.TestCase):
    def test_end_interrogation_requires_active(self):
        interrogation, _ = build_interrogation()
        with self.assertRaises(RuntimeError):
            interrogation.end_interrogation()

    def test_end_interrogation_summary(self):
        interrogation, _ = build_interrogation()
        interrogation.start_interrogation("suspect_a")

        q1 = interrogation.ask_question("Where were you?")
        interrogation.record_answer(q1.question_id, "In the kitchen.")
        interrogation.ask_question("Did you see anyone?")  # left unanswered

        outcome = interrogation.end_interrogation()

        self.assertEqual(outcome["suspect_id"], "suspect_a")
        self.assertEqual(outcome["questions_asked"], 2)
        self.assertEqual(outcome["answers_recorded"], 1)
        self.assertEqual(len(outcome["unanswered_questions"]), 1)
        self.assertEqual(outcome["contradictions"], [])
        self.assertEqual(interrogation.status, "ended")

    def test_end_interrogation_includes_contradictions(self):
        interrogation, _ = build_interrogation()
        interrogation.start_interrogation("suspect_a")

        q1 = interrogation.ask_question("Where were you?")
        interrogation.record_answer(q1.question_id, "Kitchen")
        q2 = interrogation.ask_question("Where were you?")
        interrogation.record_answer(q2.question_id, "Garden")

        outcome = interrogation.end_interrogation()
        self.assertEqual(len(outcome["contradictions"]), 1)

    def test_actions_after_end_raise(self):
        interrogation, _ = build_interrogation()
        interrogation.start_interrogation("suspect_a")
        interrogation.end_interrogation()

        with self.assertRaises(RuntimeError):
            interrogation.ask_question("Where were you?")
        with self.assertRaises(RuntimeError):
            interrogation.start_interrogation()

    def test_compare_statements_available_after_end(self):
        interrogation, _ = build_interrogation()
        interrogation.start_interrogation("suspect_a")
        q1 = interrogation.ask_question("Where were you?")
        interrogation.record_answer(q1.question_id, "In the kitchen.")
        interrogation.end_interrogation()

        # compare_statements should still be callable after ending.
        contradictions = interrogation.compare_statements()
        self.assertEqual(contradictions, [])


if __name__ == "__main__":
    unittest.main()
