"""
Unit tests for the Evidence and EvidenceManager classes
(game/evidence.py).

Run with:
    python -m unittest tests.test_evidence
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.evidence import Evidence, EvidenceManager, VALID_IMPORTANCE_LEVELS


def make_evidence(**overrides) -> Evidence:
    """Helper to build a valid Evidence item with sensible defaults."""
    defaults = dict(
        evidence_id="evidence_test",
        name="Test Evidence",
        description="A test piece of evidence.",
        evidence_type="physical",
        location_found="Test Location",
    )
    defaults.update(overrides)
    return Evidence(**defaults)


class TestEvidenceCreation(unittest.TestCase):
    def test_valid_creation_defaults(self):
        evidence = make_evidence()
        self.assertEqual(evidence.evidence_id, "evidence_test")
        self.assertEqual(evidence.importance, "low")
        self.assertFalse(evidence.discovered)
        self.assertEqual(evidence.related_suspects, [])

    def test_missing_required_field_raises(self):
        with self.assertRaises(ValueError):
            Evidence(
                evidence_id="",
                name="Test",
                description="desc",
                evidence_type="physical",
                location_found="loc",
            )

    def test_non_string_field_raises(self):
        with self.assertRaises(ValueError):
            make_evidence(name=123)

    def test_invalid_importance_raises(self):
        with self.assertRaises(ValueError):
            make_evidence(importance="extreme")

    def test_all_valid_importance_levels_accepted(self):
        for level in VALID_IMPORTANCE_LEVELS:
            evidence = make_evidence(importance=level)
            self.assertEqual(evidence.importance, level)

    def test_discovered_not_bool_raises(self):
        with self.assertRaises(ValueError):
            make_evidence(discovered="yes")

    def test_initial_related_suspects_copied_not_shared(self):
        suspects = ["Alice"]
        evidence = make_evidence(related_suspects=suspects, discovered=True)
        evidence.link_suspect("Bob")
        self.assertNotIn("Bob", suspects)


class TestDiscovery(unittest.TestCase):
    def setUp(self):
        self.evidence = make_evidence()

    def test_discover(self):
        self.assertFalse(self.evidence.is_discovered())
        self.evidence.discover()
        self.assertTrue(self.evidence.is_discovered())
        self.assertTrue(self.evidence.discovered)

    def test_discover_twice_raises(self):
        self.evidence.discover()
        with self.assertRaises(RuntimeError):
            self.evidence.discover()

    def test_starts_discovered_from_constructor(self):
        evidence = make_evidence(discovered=True)
        self.assertTrue(evidence.is_discovered())


class TestSuspectLinking(unittest.TestCase):
    def setUp(self):
        self.evidence = make_evidence()

    def test_link_suspect(self):
        self.evidence.link_suspect("Butler James")
        self.assertIn("Butler James", self.evidence.related_suspects)

    def test_link_duplicate_suspect_not_added_twice(self):
        self.evidence.link_suspect("Butler James")
        self.evidence.link_suspect("Butler James")
        self.assertEqual(self.evidence.related_suspects.count("Butler James"), 1)

    def test_link_empty_suspect_raises(self):
        with self.assertRaises(ValueError):
            self.evidence.link_suspect("")


class TestImportance(unittest.TestCase):
    def setUp(self):
        self.evidence = make_evidence()

    def test_update_importance(self):
        self.evidence.update_importance("critical")
        self.assertEqual(self.evidence.importance, "critical")

    def test_update_importance_invalid_raises(self):
        with self.assertRaises(ValueError):
            self.evidence.update_importance("bogus")


class TestInfoRetrievalHidesSolutionUntilDiscovered(unittest.TestCase):
    def test_get_info_before_discovery_hides_sensitive_fields(self):
        evidence = make_evidence(importance="critical")
        evidence.link_suspect("Butler James")

        info = evidence.get_info()

        self.assertEqual(info["evidence_id"], "evidence_test")
        self.assertFalse(info["discovered"])
        self.assertNotIn("description", info)
        self.assertNotIn("importance", info)
        self.assertNotIn("related_suspects", info)

    def test_get_info_after_discovery_reveals_full_details(self):
        evidence = make_evidence(importance="critical")
        evidence.link_suspect("Butler James")
        evidence.discover()

        info = evidence.get_info()

        self.assertTrue(info["discovered"])
        self.assertEqual(info["description"], "A test piece of evidence.")
        self.assertEqual(info["importance"], "critical")
        self.assertEqual(info["related_suspects"], ["Butler James"])

    def test_get_info_returns_copy_of_related_suspects(self):
        evidence = make_evidence()
        evidence.link_suspect("Butler James")
        evidence.discover()

        info = evidence.get_info()
        info["related_suspects"].append("injected")
        self.assertNotIn("injected", evidence.related_suspects)

    def test_to_dict_always_includes_full_data_regardless_of_discovery(self):
        evidence = make_evidence(importance="high")
        evidence.link_suspect("Butler James")

        data = evidence.to_dict()

        self.assertFalse(data["discovered"])
        self.assertEqual(data["importance"], "high")
        self.assertEqual(data["related_suspects"], ["Butler James"])

    def test_from_dict_round_trip(self):
        original = make_evidence(importance="high")
        original.link_suspect("Butler James")
        original.discover()

        rebuilt = Evidence.from_dict(original.to_dict())

        self.assertEqual(rebuilt.evidence_id, original.evidence_id)
        self.assertEqual(rebuilt.importance, original.importance)
        self.assertEqual(rebuilt.related_suspects, original.related_suspects)
        self.assertTrue(rebuilt.discovered)

    def test_from_dict_missing_field_raises(self):
        with self.assertRaises(KeyError):
            Evidence.from_dict({"evidence_id": "x", "name": "y"})


class TestEvidenceManager(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.evidence_dir = Path(self.tmp_dir.name)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def _write_file(self, filename: str, data) -> None:
        path = self.evidence_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            if isinstance(data, str):
                f.write(data)  # raw invalid content
            else:
                json.dump(data, f)

    def _valid_record(self, **overrides) -> dict:
        record = dict(
            evidence_id="evidence_a",
            name="Evidence A",
            description="desc",
            evidence_type="physical",
            location_found="loc",
        )
        record.update(overrides)
        return record

    def test_add_evidence_directly(self):
        manager = EvidenceManager()
        evidence = make_evidence()
        manager.add_evidence(evidence)

        self.assertEqual(len(manager), 1)
        self.assertIs(manager.get_evidence("evidence_test"), evidence)

    def test_add_duplicate_evidence_raises(self):
        manager = EvidenceManager()
        manager.add_evidence(make_evidence(evidence_id="dup"))
        with self.assertRaises(ValueError):
            manager.add_evidence(make_evidence(evidence_id="dup"))

    def test_add_wrong_type_raises(self):
        manager = EvidenceManager()
        with self.assertRaises(TypeError):
            manager.add_evidence({"evidence_id": "not_an_evidence_object"})

    def test_load_single_object_file(self):
        self._write_file("evidence_a.json", self._valid_record())
        manager = EvidenceManager(evidence_dir=str(self.evidence_dir))
        loaded = manager.load_all_evidence()

        self.assertEqual(len(loaded), 1)
        self.assertEqual(len(manager), 1)
        self.assertEqual(manager.get_load_errors(), [])

    def test_load_list_of_objects_file(self):
        self._write_file(
            "case_evidence.json",
            [
                self._valid_record(evidence_id="e1", name="Evidence One"),
                self._valid_record(evidence_id="e2", name="Evidence Two"),
            ],
        )
        manager = EvidenceManager(evidence_dir=str(self.evidence_dir))
        loaded = manager.load_all_evidence()

        self.assertEqual(len(loaded), 2)
        self.assertEqual(len(manager), 2)

    def test_load_missing_directory(self):
        manager = EvidenceManager(
            evidence_dir=str(self.evidence_dir / "does_not_exist")
        )
        loaded = manager.load_all_evidence()

        self.assertEqual(loaded, [])
        self.assertEqual(len(manager), 0)
        self.assertEqual(len(manager.get_load_errors()), 1)

    def test_load_all_evidence_without_directory_raises(self):
        manager = EvidenceManager()  # no default dir set
        with self.assertRaises(ValueError):
            manager.load_all_evidence()

    def test_load_skips_invalid_json(self):
        self._write_file("broken.json", "{not valid json")
        self._write_file("good.json", self._valid_record())

        manager = EvidenceManager(evidence_dir=str(self.evidence_dir))
        loaded = manager.load_all_evidence()

        self.assertEqual(len(loaded), 1)
        self.assertEqual(len(manager.get_load_errors()), 1)

    def test_load_skips_missing_required_fields(self):
        self._write_file("incomplete.json", {"evidence_id": "incomplete"})

        manager = EvidenceManager(evidence_dir=str(self.evidence_dir))
        loaded = manager.load_all_evidence()

        self.assertEqual(loaded, [])
        self.assertEqual(len(manager.get_load_errors()), 1)

    def test_load_skips_invalid_importance(self):
        self._write_file("bad_importance.json", self._valid_record(importance="extreme"))

        manager = EvidenceManager(evidence_dir=str(self.evidence_dir))
        loaded = manager.load_all_evidence()

        self.assertEqual(loaded, [])
        self.assertEqual(len(manager.get_load_errors()), 1)

    def test_load_skips_non_object_entries_in_list(self):
        self._write_file("mixed.json", [self._valid_record(), "not_an_object", 42])

        manager = EvidenceManager(evidence_dir=str(self.evidence_dir))
        loaded = manager.load_all_evidence()

        self.assertEqual(len(loaded), 1)
        self.assertEqual(len(manager.get_load_errors()), 2)

    def test_get_discovered_and_undiscovered_evidence(self):
        manager = EvidenceManager()
        found = make_evidence(evidence_id="e1", discovered=True)
        not_found = make_evidence(evidence_id="e2", discovered=False)
        manager.add_evidence(found)
        manager.add_evidence(not_found)

        self.assertEqual(manager.get_discovered_evidence(), [found])
        self.assertEqual(manager.get_undiscovered_evidence(), [not_found])

    def test_discover_evidence_via_manager(self):
        manager = EvidenceManager()
        evidence = make_evidence()
        manager.add_evidence(evidence)

        result = manager.discover_evidence("evidence_test")

        self.assertTrue(result.is_discovered())
        self.assertIs(result, evidence)

    def test_discover_evidence_unknown_id_raises(self):
        manager = EvidenceManager()
        with self.assertRaises(KeyError):
            manager.discover_evidence("does_not_exist")

    def test_get_evidence_by_suspect_only_returns_discovered(self):
        manager = EvidenceManager()
        linked_undiscovered = make_evidence(
            evidence_id="e1", related_suspects=["Butler James"], discovered=False
        )
        linked_discovered = make_evidence(
            evidence_id="e2", related_suspects=["Butler James"], discovered=True
        )
        manager.add_evidence(linked_undiscovered)
        manager.add_evidence(linked_discovered)

        results = manager.get_evidence_by_suspect("Butler James")

        self.assertEqual(results, [linked_discovered])


if __name__ == "__main__":
    unittest.main()
