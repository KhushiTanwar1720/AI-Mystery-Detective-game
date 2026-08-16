"""
Unit tests for the Case and CaseManager classes (game/case.py).

Run with:
    python -m unittest tests.test_case
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.case import Case, CaseManager


def make_case(**overrides) -> Case:
    """Helper to build a valid Case with sensible defaults."""
    defaults = dict(
        case_id="case_test",
        title="Test Case",
        description="A case used for testing.",
        location="Test Location",
        crime_type="theft",
        difficulty="easy",
        correct_suspect="Suspect A",
    )
    defaults.update(overrides)
    return Case(**defaults)


class TestCaseCreation(unittest.TestCase):
    def test_valid_creation_defaults(self):
        case = make_case()
        self.assertEqual(case.case_id, "case_test")
        self.assertEqual(case.status, "not_started")
        self.assertEqual(case.suspects, [])
        self.assertEqual(case.evidence, [])
        self.assertEqual(case.clues, [])

    def test_missing_required_field_raises(self):
        with self.assertRaises(ValueError):
            Case(
                case_id="",
                title="Test",
                description="desc",
                location="loc",
                crime_type="theft",
                difficulty="easy",
                correct_suspect="A",
            )

    def test_invalid_status_raises(self):
        with self.assertRaises(ValueError):
            make_case(status="bogus_status")

    def test_initial_lists_are_copied_not_shared(self):
        suspects = ["A", "B"]
        case = make_case(suspects=suspects)
        case.add_suspect("C")
        self.assertNotIn("C", suspects)  # original list untouched


class TestCaseMutation(unittest.TestCase):
    def setUp(self):
        self.case = make_case()

    def test_add_suspect(self):
        self.case.add_suspect("Suspect B")
        self.assertIn("Suspect B", self.case.suspects)

    def test_add_duplicate_suspect_not_added_twice(self):
        self.case.add_suspect("Suspect B")
        self.case.add_suspect("Suspect B")
        self.assertEqual(self.case.suspects.count("Suspect B"), 1)

    def test_add_empty_suspect_raises(self):
        with self.assertRaises(ValueError):
            self.case.add_suspect("")

    def test_add_evidence(self):
        self.case.add_evidence("bloody glove")
        self.assertIn("bloody glove", self.case.evidence)

    def test_add_empty_evidence_raises(self):
        with self.assertRaises(ValueError):
            self.case.add_evidence("")

    def test_add_clue(self):
        self.case.add_clue("torn letter")
        self.assertIn("torn letter", self.case.clues)

    def test_add_empty_clue_raises(self):
        with self.assertRaises(ValueError):
            self.case.add_clue("")


class TestCaseStatusFlow(unittest.TestCase):
    def setUp(self):
        self.case = make_case(correct_suspect="Suspect A")

    def test_start(self):
        self.case.start()
        self.assertEqual(self.case.get_status(), "in_progress")

    def test_complete_case_correct_suspect(self):
        self.case.start()
        result = self.case.complete_case("Suspect A")
        self.assertTrue(result)
        self.assertEqual(self.case.get_status(), "solved")
        self.assertTrue(self.case.is_solved())

    def test_complete_case_wrong_suspect(self):
        self.case.start()
        result = self.case.complete_case("Suspect B")
        self.assertFalse(result)
        self.assertEqual(self.case.get_status(), "failed")
        self.assertFalse(self.case.is_solved())

    def test_complete_case_without_starting_raises(self):
        with self.assertRaises(RuntimeError):
            self.case.complete_case("Suspect A")

    def test_start_after_solved_raises(self):
        self.case.start()
        self.case.complete_case("Suspect A")
        with self.assertRaises(RuntimeError):
            self.case.start()

    def test_complete_case_empty_accusation_raises(self):
        self.case.start()
        with self.assertRaises(ValueError):
            self.case.complete_case("")


class TestCaseInfoRetrieval(unittest.TestCase):
    def test_get_info_excludes_correct_suspect(self):
        case = make_case(correct_suspect="Suspect A")
        info = case.get_info()
        self.assertNotIn("correct_suspect", info)
        self.assertEqual(info["case_id"], "case_test")

    def test_to_dict_includes_correct_suspect(self):
        case = make_case(correct_suspect="Suspect A")
        data = case.to_dict()
        self.assertEqual(data["correct_suspect"], "Suspect A")

    def test_from_dict_round_trip(self):
        original = make_case(correct_suspect="Suspect A")
        original.add_suspect("Suspect B")
        rebuilt = Case.from_dict(original.to_dict())
        self.assertEqual(rebuilt.case_id, original.case_id)
        self.assertEqual(rebuilt.suspects, original.suspects)
        self.assertEqual(rebuilt.correct_suspect, original.correct_suspect)

    def test_from_dict_missing_field_raises(self):
        with self.assertRaises(KeyError):
            Case.from_dict({"case_id": "x", "title": "y"})


class TestCaseManager(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.cases_dir = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _write_case_file(self, filename: str, data) -> None:
        path = self.cases_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            if isinstance(data, str):
                f.write(data)  # raw invalid content
            else:
                json.dump(data, f)

    def test_load_all_cases_valid_directory(self):
        self._write_case_file(
            "case_a.json",
            {
                "case_id": "case_a",
                "title": "Case A",
                "description": "desc",
                "location": "loc",
                "crime_type": "theft",
                "difficulty": "easy",
                "correct_suspect": "X",
            },
        )
        self._write_case_file(
            "case_b.json",
            {
                "case_id": "case_b",
                "title": "Case B",
                "description": "desc",
                "location": "loc",
                "crime_type": "murder",
                "difficulty": "hard",
                "correct_suspect": "Y",
            },
        )

        manager = CaseManager(cases_dir=str(self.cases_dir))
        loaded = manager.load_all_cases()

        self.assertEqual(len(loaded), 2)
        self.assertEqual(len(manager), 2)
        self.assertEqual(manager.get_load_errors(), [])

    def test_load_all_cases_missing_directory(self):
        manager = CaseManager(cases_dir=str(self.cases_dir / "does_not_exist"))
        loaded = manager.load_all_cases()

        self.assertEqual(loaded, [])
        self.assertEqual(len(manager), 0)
        self.assertEqual(len(manager.get_load_errors()), 1)

    def test_load_all_cases_skips_invalid_json(self):
        self._write_case_file("broken.json", "{not valid json")
        self._write_case_file(
            "good.json",
            {
                "case_id": "good_case",
                "title": "Good Case",
                "description": "desc",
                "location": "loc",
                "crime_type": "theft",
                "difficulty": "easy",
                "correct_suspect": "X",
            },
        )

        manager = CaseManager(cases_dir=str(self.cases_dir))
        loaded = manager.load_all_cases()

        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].case_id, "good_case")
        self.assertEqual(len(manager.get_load_errors()), 1)

    def test_load_all_cases_skips_missing_required_fields(self):
        self._write_case_file("incomplete.json", {"case_id": "incomplete"})

        manager = CaseManager(cases_dir=str(self.cases_dir))
        loaded = manager.load_all_cases()

        self.assertEqual(loaded, [])
        self.assertEqual(len(manager.get_load_errors()), 1)

    def test_get_case_by_id(self):
        self._write_case_file(
            "case_a.json",
            {
                "case_id": "case_a",
                "title": "Case A",
                "description": "desc",
                "location": "loc",
                "crime_type": "theft",
                "difficulty": "easy",
                "correct_suspect": "X",
            },
        )
        manager = CaseManager(cases_dir=str(self.cases_dir))
        manager.load_all_cases()

        found = manager.get_case("case_a")
        self.assertIsNotNone(found)
        self.assertEqual(found.title, "Case A")
        self.assertIsNone(manager.get_case("does_not_exist"))

    def test_get_cases_by_difficulty(self):
        self._write_case_file(
            "case_a.json",
            {
                "case_id": "case_a",
                "title": "Case A",
                "description": "desc",
                "location": "loc",
                "crime_type": "theft",
                "difficulty": "easy",
                "correct_suspect": "X",
            },
        )
        self._write_case_file(
            "case_b.json",
            {
                "case_id": "case_b",
                "title": "Case B",
                "description": "desc",
                "location": "loc",
                "crime_type": "murder",
                "difficulty": "hard",
                "correct_suspect": "Y",
            },
        )
        manager = CaseManager(cases_dir=str(self.cases_dir))
        manager.load_all_cases()

        easy_cases = manager.get_cases_by_difficulty("easy")
        self.assertEqual(len(easy_cases), 1)
        self.assertEqual(easy_cases[0].case_id, "case_a")

    def test_add_case_directly(self):
        manager = CaseManager(cases_dir=str(self.cases_dir))
        case = make_case(case_id="manual_case")
        manager.add_case(case)

        self.assertEqual(len(manager), 1)
        self.assertIs(manager.get_case("manual_case"), case)

    def test_add_duplicate_case_raises(self):
        manager = CaseManager(cases_dir=str(self.cases_dir))
        manager.add_case(make_case(case_id="dup"))
        with self.assertRaises(ValueError):
            manager.add_case(make_case(case_id="dup"))

    def test_add_case_wrong_type_raises(self):
        manager = CaseManager(cases_dir=str(self.cases_dir))
        with self.assertRaises(TypeError):
            manager.add_case({"case_id": "not_a_case_object"})


if __name__ == "__main__":
    unittest.main()
