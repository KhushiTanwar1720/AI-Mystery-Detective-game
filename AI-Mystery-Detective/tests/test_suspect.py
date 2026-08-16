"""
Unit tests for the Suspect and SuspectManager classes (game/suspect.py).

Run with:
    python -m unittest tests.test_suspect
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.suspect import Suspect, SuspectManager, MIN_SUSPICION_LEVEL, MAX_SUSPICION_LEVEL


def make_suspect(**overrides) -> Suspect:
    """Helper to build a valid Suspect with sensible defaults."""
    defaults = dict(
        suspect_id="suspect_test",
        name="Test Suspect",
        age=35,
        occupation="Clerk",
        description="An ordinary-looking clerk.",
        relationship_to_victim="Coworker",
    )
    defaults.update(overrides)
    return Suspect(**defaults)


class TestSuspectCreation(unittest.TestCase):
    def test_valid_creation_defaults(self):
        suspect = make_suspect()
        self.assertEqual(suspect.suspect_id, "suspect_test")
        self.assertEqual(suspect.alibi, "Unknown")
        self.assertEqual(suspect.behavior, [])
        self.assertEqual(suspect.statements, [])
        self.assertEqual(suspect.suspicion_level, 0)

    def test_missing_required_field_raises(self):
        with self.assertRaises(ValueError):
            Suspect(
                suspect_id="",
                name="Test",
                age=30,
                occupation="Clerk",
                description="desc",
                relationship_to_victim="Coworker",
            )

    def test_non_string_field_raises(self):
        with self.assertRaises(ValueError):
            make_suspect(name=123)

    def test_age_not_int_raises(self):
        with self.assertRaises(ValueError):
            make_suspect(age=30.5)

    def test_age_bool_raises(self):
        with self.assertRaises(ValueError):
            make_suspect(age=True)

    def test_age_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            make_suspect(age=-1)
        with self.assertRaises(ValueError):
            make_suspect(age=200)

    def test_suspicion_level_not_int_raises(self):
        with self.assertRaises(ValueError):
            make_suspect(suspicion_level=5.5)

    def test_suspicion_level_clamped_on_init(self):
        suspect = make_suspect(suspicion_level=999)
        self.assertEqual(suspect.suspicion_level, MAX_SUSPICION_LEVEL)
        suspect2 = make_suspect(suspicion_level=-50)
        self.assertEqual(suspect2.suspicion_level, MIN_SUSPICION_LEVEL)

    def test_initial_lists_are_copied_not_shared(self):
        statements = ["I was home."]
        suspect = make_suspect(statements=statements)
        suspect.add_statement("New statement")
        self.assertNotIn("New statement", statements)


class TestStatements(unittest.TestCase):
    def setUp(self):
        self.suspect = make_suspect()

    def test_add_statement(self):
        self.suspect.add_statement("I was at home.")
        self.assertIn("I was at home.", self.suspect.get_statements())

    def test_add_duplicate_statement_allowed(self):
        # Statements are intentionally NOT deduplicated.
        self.suspect.add_statement("I was at home.")
        self.suspect.add_statement("I was at home.")
        self.assertEqual(self.suspect.statements.count("I was at home."), 2)

    def test_add_empty_statement_raises(self):
        with self.assertRaises(ValueError):
            self.suspect.add_statement("")

    def test_get_statements_returns_copy(self):
        self.suspect.add_statement("Original")
        statements = self.suspect.get_statements()
        statements.append("Mutated externally")
        self.assertNotIn("Mutated externally", self.suspect.statements)


class TestAlibiAndBehavior(unittest.TestCase):
    def setUp(self):
        self.suspect = make_suspect()

    def test_update_alibi(self):
        self.suspect.update_alibi("I was at the theater.")
        self.assertEqual(self.suspect.alibi, "I was at the theater.")

    def test_update_alibi_empty_raises(self):
        with self.assertRaises(ValueError):
            self.suspect.update_alibi("")

    def test_record_behavior(self):
        self.suspect.record_behavior("Avoided eye contact.")
        self.assertIn("Avoided eye contact.", self.suspect.behavior)

    def test_record_behavior_allows_repeats(self):
        self.suspect.record_behavior("Fidgeting.")
        self.suspect.record_behavior("Fidgeting.")
        self.assertEqual(self.suspect.behavior.count("Fidgeting."), 2)

    def test_record_behavior_empty_raises(self):
        with self.assertRaises(ValueError):
            self.suspect.record_behavior("")


class TestSuspicionLevel(unittest.TestCase):
    def setUp(self):
        self.suspect = make_suspect()

    def test_update_suspicion_level_increase(self):
        new_level = self.suspect.update_suspicion_level(20)
        self.assertEqual(new_level, 20)
        self.assertEqual(self.suspect.suspicion_level, 20)

    def test_update_suspicion_level_decrease_floors_at_min(self):
        self.suspect.update_suspicion_level(10)
        self.suspect.update_suspicion_level(-50)
        self.assertEqual(self.suspect.suspicion_level, MIN_SUSPICION_LEVEL)

    def test_update_suspicion_level_caps_at_max(self):
        self.suspect.update_suspicion_level(500)
        self.assertEqual(self.suspect.suspicion_level, MAX_SUSPICION_LEVEL)

    def test_update_suspicion_level_non_int_raises(self):
        with self.assertRaises(ValueError):
            self.suspect.update_suspicion_level(2.5)

    def test_reset_suspicion_level(self):
        self.suspect.update_suspicion_level(75)
        self.suspect.reset_suspicion_level()
        self.assertEqual(self.suspect.suspicion_level, MIN_SUSPICION_LEVEL)


class TestSuspectInfoRetrieval(unittest.TestCase):
    def test_get_info_contains_all_fields(self):
        suspect = make_suspect()
        suspect.add_statement("I was home.")
        suspect.record_behavior("Nervous laugh.")
        suspect.update_suspicion_level(10)

        info = suspect.get_info()

        self.assertEqual(info["suspect_id"], "suspect_test")
        self.assertEqual(info["statements"], ["I was home."])
        self.assertEqual(info["behavior"], ["Nervous laugh."])
        self.assertEqual(info["suspicion_level"], 10)

    def test_get_info_returns_copies_of_lists(self):
        suspect = make_suspect()
        info = suspect.get_info()
        info["statements"].append("injected")
        self.assertNotIn("injected", suspect.statements)

    def test_from_dict_round_trip(self):
        original = make_suspect()
        original.add_statement("I was home.")
        original.update_suspicion_level(15)
        rebuilt = Suspect.from_dict(original.to_dict())

        self.assertEqual(rebuilt.suspect_id, original.suspect_id)
        self.assertEqual(rebuilt.statements, original.statements)
        self.assertEqual(rebuilt.suspicion_level, original.suspicion_level)

    def test_from_dict_missing_field_raises(self):
        with self.assertRaises(KeyError):
            Suspect.from_dict({"suspect_id": "x", "name": "y"})


class TestSuspectManager(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.suspects_dir = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _write_file(self, filename: str, data) -> None:
        path = self.suspects_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            if isinstance(data, str):
                f.write(data)  # raw invalid content
            else:
                json.dump(data, f)

    def _valid_record(self, **overrides) -> dict:
        record = dict(
            suspect_id="suspect_a",
            name="Suspect A",
            age=40,
            occupation="Gardener",
            description="desc",
            relationship_to_victim="Neighbor",
        )
        record.update(overrides)
        return record

    def test_add_suspect_directly(self):
        manager = SuspectManager()
        suspect = make_suspect()
        manager.add_suspect(suspect)

        self.assertEqual(len(manager), 1)
        self.assertIs(manager.get_suspect("suspect_test"), suspect)

    def test_add_duplicate_suspect_raises(self):
        manager = SuspectManager()
        manager.add_suspect(make_suspect(suspect_id="dup"))
        with self.assertRaises(ValueError):
            manager.add_suspect(make_suspect(suspect_id="dup"))

    def test_add_wrong_type_raises(self):
        manager = SuspectManager()
        with self.assertRaises(TypeError):
            manager.add_suspect({"suspect_id": "not_a_suspect_object"})

    def test_load_single_object_file(self):
        self._write_file("suspect_a.json", self._valid_record())
        manager = SuspectManager(suspects_dir=str(self.suspects_dir))
        loaded = manager.load_all_suspects()

        self.assertEqual(len(loaded), 1)
        self.assertEqual(len(manager), 1)
        self.assertEqual(manager.get_load_errors(), [])

    def test_load_list_of_objects_file(self):
        self._write_file(
            "case_suspects.json",
            [
                self._valid_record(suspect_id="s1", name="Suspect One"),
                self._valid_record(suspect_id="s2", name="Suspect Two"),
            ],
        )
        manager = SuspectManager(suspects_dir=str(self.suspects_dir))
        loaded = manager.load_all_suspects()

        self.assertEqual(len(loaded), 2)
        self.assertEqual(len(manager), 2)

    def test_load_missing_directory(self):
        manager = SuspectManager(
            suspects_dir=str(self.suspects_dir / "does_not_exist")
        )
        loaded = manager.load_all_suspects()

        self.assertEqual(loaded, [])
        self.assertEqual(len(manager), 0)
        self.assertEqual(len(manager.get_load_errors()), 1)

    def test_load_all_suspects_without_directory_raises(self):
        manager = SuspectManager()  # no default dir set
        with self.assertRaises(ValueError):
            manager.load_all_suspects()

    def test_load_skips_invalid_json(self):
        self._write_file("broken.json", "{not valid json")
        self._write_file("good.json", self._valid_record())

        manager = SuspectManager(suspects_dir=str(self.suspects_dir))
        loaded = manager.load_all_suspects()

        self.assertEqual(len(loaded), 1)
        self.assertEqual(len(manager.get_load_errors()), 1)

    def test_load_skips_missing_required_fields(self):
        self._write_file("incomplete.json", {"suspect_id": "incomplete"})

        manager = SuspectManager(suspects_dir=str(self.suspects_dir))
        loaded = manager.load_all_suspects()

        self.assertEqual(loaded, [])
        self.assertEqual(len(manager.get_load_errors()), 1)

    def test_load_skips_non_object_entries_in_list(self):
        self._write_file("mixed.json", [self._valid_record(), "not_an_object", 42])

        manager = SuspectManager(suspects_dir=str(self.suspects_dir))
        loaded = manager.load_all_suspects()

        self.assertEqual(len(loaded), 1)
        self.assertEqual(len(manager.get_load_errors()), 2)

    def test_get_suspects_by_names(self):
        manager = SuspectManager()
        manager.add_suspect(make_suspect(suspect_id="s1", name="Alice"))
        manager.add_suspect(make_suspect(suspect_id="s2", name="Bob"))

        matches = manager.get_suspects_by_names(["Alice", "Someone Else"])
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].name, "Alice")

    def test_get_suspects_for_case(self):
        class FakeCase:
            suspects = ["Alice", "Bob"]

        manager = SuspectManager()
        manager.add_suspect(make_suspect(suspect_id="s1", name="Alice"))
        manager.add_suspect(make_suspect(suspect_id="s2", name="Bob"))
        manager.add_suspect(make_suspect(suspect_id="s3", name="Charlie"))

        matches = manager.get_suspects_for_case(FakeCase())
        names = {s.name for s in matches}
        self.assertEqual(names, {"Alice", "Bob"})


if __name__ == "__main__":
    unittest.main()
