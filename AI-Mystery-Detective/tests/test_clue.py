"""
Unit tests for the Clue and ClueManager classes (game/clue.py).

Run with:
    python -m unittest tests.test_clue
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.clue import Clue, ClueManager, VALID_IMPORTANCE_LEVELS


def make_clue(**overrides) -> Clue:
    """Helper to build a valid Clue with sensible defaults."""
    defaults = dict(
        clue_id="clue_test",
        description="A test clue description.",
        source="Test source",
        location="Test location",
    )
    defaults.update(overrides)
    return Clue(**defaults)


class TestClueCreation(unittest.TestCase):
    def test_valid_creation_defaults(self):
        clue = make_clue()
        self.assertEqual(clue.clue_id, "clue_test")
        self.assertEqual(clue.importance, "low")
        self.assertFalse(clue.discovered)
        self.assertEqual(clue.related_evidence, [])
        self.assertEqual(clue.related_suspects, [])

    def test_missing_required_field_raises(self):
        with self.assertRaises(ValueError):
            Clue(clue_id="", description="desc", source="src", location="loc")

    def test_non_string_field_raises(self):
        with self.assertRaises(ValueError):
            make_clue(source=123)

    def test_invalid_importance_raises(self):
        with self.assertRaises(ValueError):
            make_clue(importance="extreme")

    def test_all_valid_importance_levels_accepted(self):
        for level in VALID_IMPORTANCE_LEVELS:
            clue = make_clue(importance=level)
            self.assertEqual(clue.importance, level)

    def test_discovered_not_bool_raises(self):
        with self.assertRaises(ValueError):
            make_clue(discovered="yes")

    def test_initial_lists_copied_not_shared(self):
        evidence_list = ["e1"]
        suspects_list = ["Alice"]
        clue = make_clue(
            related_evidence=evidence_list,
            related_suspects=suspects_list,
            discovered=True,
        )
        clue.link_evidence("e2")
        clue.link_suspect("Bob")
        self.assertNotIn("e2", evidence_list)
        self.assertNotIn("Bob", suspects_list)


class TestDiscovery(unittest.TestCase):
    def setUp(self):
        self.clue = make_clue()

    def test_discover(self):
        self.assertFalse(self.clue.is_discovered())
        self.clue.discover()
        self.assertTrue(self.clue.is_discovered())
        self.assertTrue(self.clue.discovered)

    def test_discover_twice_raises(self):
        self.clue.discover()
        with self.assertRaises(RuntimeError):
            self.clue.discover()

    def test_starts_discovered_from_constructor(self):
        clue = make_clue(discovered=True)
        self.assertTrue(clue.is_discovered())


class TestLinking(unittest.TestCase):
    def setUp(self):
        self.clue = make_clue()

    def test_link_evidence(self):
        self.clue.link_evidence("evidence_1")
        self.assertIn("evidence_1", self.clue.related_evidence)

    def test_link_duplicate_evidence_not_added_twice(self):
        self.clue.link_evidence("evidence_1")
        self.clue.link_evidence("evidence_1")
        self.assertEqual(self.clue.related_evidence.count("evidence_1"), 1)

    def test_link_empty_evidence_raises(self):
        with self.assertRaises(ValueError):
            self.clue.link_evidence("")

    def test_link_suspect(self):
        self.clue.link_suspect("Butler James")
        self.assertIn("Butler James", self.clue.related_suspects)

    def test_link_duplicate_suspect_not_added_twice(self):
        self.clue.link_suspect("Butler James")
        self.clue.link_suspect("Butler James")
        self.assertEqual(self.clue.related_suspects.count("Butler James"), 1)

    def test_link_empty_suspect_raises(self):
        with self.assertRaises(ValueError):
            self.clue.link_suspect("")


class TestImportance(unittest.TestCase):
    def setUp(self):
        self.clue = make_clue()

    def test_update_importance(self):
        self.clue.update_importance("critical")
        self.assertEqual(self.clue.importance, "critical")

    def test_update_importance_invalid_raises(self):
        with self.assertRaises(ValueError):
            self.clue.update_importance("bogus")


class TestInfoRetrievalHidesSolutionUntilDiscovered(unittest.TestCase):
    def test_get_info_before_discovery_hides_sensitive_fields(self):
        clue = make_clue(importance="critical")
        clue.link_evidence("evidence_1")
        clue.link_suspect("Butler James")

        info = clue.get_info()

        self.assertEqual(info["clue_id"], "clue_test")
        self.assertFalse(info["discovered"])
        self.assertNotIn("description", info)
        self.assertNotIn("importance", info)
        self.assertNotIn("related_evidence", info)
        self.assertNotIn("related_suspects", info)

    def test_get_info_after_discovery_reveals_full_details(self):
        clue = make_clue(importance="critical")
        clue.link_evidence("evidence_1")
        clue.link_suspect("Butler James")
        clue.discover()

        info = clue.get_info()

        self.assertTrue(info["discovered"])
        self.assertEqual(info["description"], "A test clue description.")
        self.assertEqual(info["importance"], "critical")
        self.assertEqual(info["related_evidence"], ["evidence_1"])
        self.assertEqual(info["related_suspects"], ["Butler James"])

    def test_get_info_returns_copies_of_lists(self):
        clue = make_clue()
        clue.link_evidence("evidence_1")
        clue.link_suspect("Butler James")
        clue.discover()

        info = clue.get_info()
        info["related_evidence"].append("injected")
        info["related_suspects"].append("injected")
        self.assertNotIn("injected", clue.related_evidence)
        self.assertNotIn("injected", clue.related_suspects)

    def test_to_dict_always_includes_full_data_regardless_of_discovery(self):
        clue = make_clue(importance="high")
        clue.link_evidence("evidence_1")
        clue.link_suspect("Butler James")

        data = clue.to_dict()

        self.assertFalse(data["discovered"])
        self.assertEqual(data["importance"], "high")
        self.assertEqual(data["related_evidence"], ["evidence_1"])
        self.assertEqual(data["related_suspects"], ["Butler James"])

    def test_from_dict_round_trip(self):
        original = make_clue(importance="high")
        original.link_evidence("evidence_1")
        original.link_suspect("Butler James")
        original.discover()

        rebuilt = Clue.from_dict(original.to_dict())

        self.assertEqual(rebuilt.clue_id, original.clue_id)
        self.assertEqual(rebuilt.importance, original.importance)
        self.assertEqual(rebuilt.related_evidence, original.related_evidence)
        self.assertEqual(rebuilt.related_suspects, original.related_suspects)
        self.assertTrue(rebuilt.discovered)

    def test_from_dict_missing_field_raises(self):
        with self.assertRaises(KeyError):
            Clue.from_dict({"clue_id": "x", "description": "y"})


class TestClueManager(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.clues_dir = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _write_file(self, filename: str, data) -> None:
        path = self.clues_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            if isinstance(data, str):
                f.write(data)  # raw invalid content
            else:
                json.dump(data, f)

    def _valid_record(self, **overrides) -> dict:
        record = dict(
            clue_id="clue_a",
            description="desc",
            source="src",
            location="loc",
        )
        record.update(overrides)
        return record

    def test_add_clue_directly(self):
        manager = ClueManager()
        clue = make_clue()
        manager.add_clue(clue)

        self.assertEqual(len(manager), 1)
        self.assertIs(manager.get_clue("clue_test"), clue)

    def test_add_duplicate_clue_raises(self):
        manager = ClueManager()
        manager.add_clue(make_clue(clue_id="dup"))
        with self.assertRaises(ValueError):
            manager.add_clue(make_clue(clue_id="dup"))

    def test_add_wrong_type_raises(self):
        manager = ClueManager()
        with self.assertRaises(TypeError):
            manager.add_clue({"clue_id": "not_a_clue_object"})

    def test_load_single_object_file(self):
        self._write_file("clue_a.json", self._valid_record())
        manager = ClueManager(clues_dir=str(self.clues_dir))
        loaded = manager.load_all_clues()

        self.assertEqual(len(loaded), 1)
        self.assertEqual(len(manager), 1)
        self.assertEqual(manager.get_load_errors(), [])

    def test_load_list_of_objects_file(self):
        self._write_file(
            "case_clues.json",
            [
                self._valid_record(clue_id="c1"),
                self._valid_record(clue_id="c2"),
            ],
        )
        manager = ClueManager(clues_dir=str(self.clues_dir))
        loaded = manager.load_all_clues()

        self.assertEqual(len(loaded), 2)
        self.assertEqual(len(manager), 2)

    def test_load_missing_directory(self):
        manager = ClueManager(clues_dir=str(self.clues_dir / "does_not_exist"))
        loaded = manager.load_all_clues()

        self.assertEqual(loaded, [])
        self.assertEqual(len(manager), 0)
        self.assertEqual(len(manager.get_load_errors()), 1)

    def test_load_all_clues_without_directory_raises(self):
        manager = ClueManager()  # no default dir set
        with self.assertRaises(ValueError):
            manager.load_all_clues()

    def test_load_skips_invalid_json(self):
        self._write_file("broken.json", "{not valid json")
        self._write_file("good.json", self._valid_record())

        manager = ClueManager(clues_dir=str(self.clues_dir))
        loaded = manager.load_all_clues()

        self.assertEqual(len(loaded), 1)
        self.assertEqual(len(manager.get_load_errors()), 1)

    def test_load_skips_missing_required_fields(self):
        self._write_file("incomplete.json", {"clue_id": "incomplete"})

        manager = ClueManager(clues_dir=str(self.clues_dir))
        loaded = manager.load_all_clues()

        self.assertEqual(loaded, [])
        self.assertEqual(len(manager.get_load_errors()), 1)

    def test_load_skips_invalid_importance(self):
        self._write_file("bad_importance.json", self._valid_record(importance="extreme"))

        manager = ClueManager(clues_dir=str(self.clues_dir))
        loaded = manager.load_all_clues()

        self.assertEqual(loaded, [])
        self.assertEqual(len(manager.get_load_errors()), 1)

    def test_load_skips_non_object_entries_in_list(self):
        self._write_file("mixed.json", [self._valid_record(), "not_an_object", 42])

        manager = ClueManager(clues_dir=str(self.clues_dir))
        loaded = manager.load_all_clues()

        self.assertEqual(len(loaded), 1)
        self.assertEqual(len(manager.get_load_errors()), 2)

    def test_get_discovered_and_undiscovered_clues(self):
        manager = ClueManager()
        found = make_clue(clue_id="c1", discovered=True)
        not_found = make_clue(clue_id="c2", discovered=False)
        manager.add_clue(found)
        manager.add_clue(not_found)

        self.assertEqual(manager.get_discovered_clues(), [found])
        self.assertEqual(manager.get_undiscovered_clues(), [not_found])

    def test_discover_clue_via_manager(self):
        manager = ClueManager()
        clue = make_clue()
        manager.add_clue(clue)

        result = manager.discover_clue("clue_test")

        self.assertTrue(result.is_discovered())
        self.assertIs(result, clue)

    def test_discover_clue_unknown_id_raises(self):
        manager = ClueManager()
        with self.assertRaises(KeyError):
            manager.discover_clue("does_not_exist")

    def test_get_clues_by_suspect_only_returns_discovered(self):
        manager = ClueManager()
        linked_undiscovered = make_clue(
            clue_id="c1", related_suspects=["Butler James"], discovered=False
        )
        linked_discovered = make_clue(
            clue_id="c2", related_suspects=["Butler James"], discovered=True
        )
        manager.add_clue(linked_undiscovered)
        manager.add_clue(linked_discovered)

        results = manager.get_clues_by_suspect("Butler James")

        self.assertEqual(results, [linked_discovered])

    def test_get_clues_by_evidence_only_returns_discovered(self):
        manager = ClueManager()
        linked_undiscovered = make_clue(
            clue_id="c1", related_evidence=["evidence_1"], discovered=False
        )
        linked_discovered = make_clue(
            clue_id="c2", related_evidence=["evidence_1"], discovered=True
        )
        manager.add_clue(linked_undiscovered)
        manager.add_clue(linked_discovered)

        results = manager.get_clues_by_evidence("evidence_1")

        self.assertEqual(results, [linked_discovered])


if __name__ == "__main__":
    unittest.main()
