"""
Unit tests for the Location and LocationManager classes (game/location.py).

Run with:
    python -m unittest tests.test_location
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.location import Location, LocationManager


def make_location(**overrides) -> Location:
    """Helper to build a valid Location with sensible defaults."""
    defaults = dict(
        location_id="loc_a",
        name="Drawing Room",
        description="An elegant sitting room.",
        location_type="room",
        connected_locations=["loc_b"],
        available_evidence=["evidence_a"],
        available_clues=["clue_a"],
    )
    defaults.update(overrides)
    return Location(**defaults)


# -- Location creation ------------------------------------------------------

class TestLocationCreation(unittest.TestCase):
    def test_create_valid_location(self):
        loc = make_location()
        self.assertEqual(loc.location_id, "loc_a")
        self.assertEqual(loc.name, "Drawing Room")
        self.assertEqual(loc.description, "An elegant sitting room.")
        self.assertEqual(loc.location_type, "room")
        self.assertEqual(loc.connected_locations, ["loc_b"])
        self.assertEqual(loc.available_evidence, ["evidence_a"])
        self.assertEqual(loc.available_clues, ["clue_a"])
        self.assertFalse(loc.visited)
        self.assertEqual(loc.visit_count, 0)

    def test_create_with_defaults(self):
        loc = Location(
            location_id="loc_x",
            name="Attic",
            description="A dusty attic.",
            location_type="room",
        )
        self.assertEqual(loc.connected_locations, [])
        self.assertEqual(loc.available_evidence, [])
        self.assertEqual(loc.available_clues, [])
        self.assertFalse(loc.visited)
        self.assertEqual(loc.visit_count, 0)

    def test_create_with_initial_visited_state(self):
        loc = Location(
            location_id="loc_x",
            name="Attic",
            description="A dusty attic.",
            location_type="room",
            visited=True,
            visit_count=3,
        )
        self.assertTrue(loc.visited)
        self.assertEqual(loc.visit_count, 3)

    def test_empty_location_id_raises(self):
        with self.assertRaises(ValueError):
            Location(location_id="", name="n", description="d", location_type="room")

    def test_non_string_name_raises(self):
        with self.assertRaises(ValueError):
            Location(location_id="loc_a", name=123, description="d", location_type="room")

    def test_empty_description_raises(self):
        with self.assertRaises(ValueError):
            Location(location_id="loc_a", name="n", description="", location_type="room")

    def test_empty_location_type_raises(self):
        with self.assertRaises(ValueError):
            Location(location_id="loc_a", name="n", description="d", location_type="")

    def test_negative_visit_count_raises(self):
        with self.assertRaises(ValueError):
            Location(
                location_id="loc_a",
                name="n",
                description="d",
                location_type="room",
                visit_count=-1,
            )

    def test_non_integer_visit_count_raises(self):
        with self.assertRaises(ValueError):
            Location(
                location_id="loc_a",
                name="n",
                description="d",
                location_type="room",
                visit_count="three",
            )

    def test_duplicate_ids_in_initial_lists_are_deduplicated(self):
        loc = make_location(
            connected_locations=["loc_b", "loc_b", "loc_c"],
            available_evidence=["evidence_a", "evidence_a"],
            available_clues=["clue_a", "clue_a"],
        )
        self.assertEqual(loc.connected_locations, ["loc_b", "loc_c"])
        self.assertEqual(loc.available_evidence, ["evidence_a"])
        self.assertEqual(loc.available_clues, ["clue_a"])


# -- Visiting / leaving / visit tracking -------------------------------------

class TestVisitingLeaving(unittest.TestCase):
    def setUp(self):
        self.loc = make_location()

    def test_visit_marks_visited(self):
        self.assertFalse(self.loc.is_visited())
        self.loc.visit()
        self.assertTrue(self.loc.is_visited())

    def test_visit_increments_visit_count(self):
        self.loc.visit()
        self.loc.visit()
        self.loc.visit()
        self.assertEqual(self.loc.visit_count, 3)

    def test_visit_returns_location_info(self):
        info = self.loc.visit()
        self.assertEqual(info["location_id"], "loc_a")
        self.assertTrue(info["visited"])
        self.assertEqual(info["visit_count"], 1)

    def test_revisit_does_not_reset_previous_visits(self):
        self.loc.visit()
        self.loc.visit()
        self.assertTrue(self.loc.is_visited())
        self.assertEqual(self.loc.visit_count, 2)

    def test_leave_does_not_raise_and_returns_none(self):
        self.loc.visit()
        result = self.loc.leave()
        self.assertIsNone(result)

    def test_leave_does_not_affect_visited_state(self):
        self.loc.visit()
        self.loc.leave()
        self.assertTrue(self.loc.is_visited())
        self.assertEqual(self.loc.visit_count, 1)

    def test_is_visited_false_before_any_visit(self):
        self.assertFalse(self.loc.is_visited())

    def test_visit_does_not_discover_evidence_or_clues(self):
        """A visit only exposes ids -- it must never auto-mark anything
        as discovered, since Location doesn't own Evidence/Clue
        objects at all."""
        info = self.loc.visit()
        self.assertEqual(info["available_evidence"], ["evidence_a"])
        self.assertEqual(info["available_clues"], ["clue_a"])
        # Location has no concept of "discovered" for evidence/clues --
        # confirm that attribute simply doesn't exist on this class.
        self.assertFalse(hasattr(self.loc, "discovered"))


# -- Connections --------------------------------------------------------------

class TestConnections(unittest.TestCase):
    def setUp(self):
        self.loc = make_location(connected_locations=[])

    def test_connect_location_adds_new_connection(self):
        added = self.loc.connect_location("loc_b")
        self.assertTrue(added)
        self.assertIn("loc_b", self.loc.connected_locations)

    def test_connect_duplicate_connection_returns_false(self):
        self.loc.connect_location("loc_b")
        added_again = self.loc.connect_location("loc_b")
        self.assertFalse(added_again)
        self.assertEqual(self.loc.connected_locations.count("loc_b"), 1)

    def test_connect_to_self_raises(self):
        with self.assertRaises(ValueError):
            self.loc.connect_location("loc_a")

    def test_connect_empty_id_raises(self):
        with self.assertRaises(ValueError):
            self.loc.connect_location("")

    def test_disconnect_existing_connection(self):
        self.loc.connect_location("loc_b")
        removed = self.loc.disconnect_location("loc_b")
        self.assertTrue(removed)
        self.assertNotIn("loc_b", self.loc.connected_locations)

    def test_disconnect_nonexistent_connection_returns_false(self):
        removed = self.loc.disconnect_location("loc_z")
        self.assertFalse(removed)

    def test_disconnect_empty_id_raises(self):
        with self.assertRaises(ValueError):
            self.loc.disconnect_location("")

    def test_get_connected_locations_returns_copy(self):
        self.loc.connect_location("loc_b")
        connections = self.loc.get_connected_locations()
        connections.append("loc_z")
        self.assertNotIn("loc_z", self.loc.connected_locations)


# -- Evidence / clue references ------------------------------------------------

class TestEvidenceAndClueReferences(unittest.TestCase):
    def setUp(self):
        self.loc = make_location(available_evidence=[], available_clues=[])

    def test_add_evidence_adds_new_id(self):
        added = self.loc.add_evidence("evidence_x")
        self.assertTrue(added)
        self.assertIn("evidence_x", self.loc.available_evidence)

    def test_add_duplicate_evidence_returns_false(self):
        self.loc.add_evidence("evidence_x")
        added_again = self.loc.add_evidence("evidence_x")
        self.assertFalse(added_again)
        self.assertEqual(self.loc.available_evidence.count("evidence_x"), 1)

    def test_add_evidence_empty_id_raises(self):
        with self.assertRaises(ValueError):
            self.loc.add_evidence("")

    def test_add_clue_adds_new_id(self):
        added = self.loc.add_clue("clue_x")
        self.assertTrue(added)
        self.assertIn("clue_x", self.loc.available_clues)

    def test_add_duplicate_clue_returns_false(self):
        self.loc.add_clue("clue_x")
        added_again = self.loc.add_clue("clue_x")
        self.assertFalse(added_again)
        self.assertEqual(self.loc.available_clues.count("clue_x"), 1)

    def test_add_clue_empty_id_raises(self):
        with self.assertRaises(ValueError):
            self.loc.add_clue("")

    def test_get_available_evidence_returns_copy(self):
        self.loc.add_evidence("evidence_x")
        result = self.loc.get_available_evidence()
        result.append("evidence_z")
        self.assertNotIn("evidence_z", self.loc.available_evidence)

    def test_get_available_clues_returns_copy(self):
        self.loc.add_clue("clue_x")
        result = self.loc.get_available_clues()
        result.append("clue_z")
        self.assertNotIn("clue_z", self.loc.available_clues)


# -- Info retrieval / reset -----------------------------------------------------

class TestLocationInfoAndReset(unittest.TestCase):
    def test_get_location_info_contains_all_fields(self):
        loc = make_location()
        info = loc.get_location_info()
        for field in (
            "location_id",
            "name",
            "description",
            "location_type",
            "connected_locations",
            "available_evidence",
            "available_clues",
            "visited",
            "visit_count",
        ):
            self.assertIn(field, info)

    def test_get_location_info_returns_copies_of_lists(self):
        loc = make_location()
        info = loc.get_location_info()
        info["connected_locations"].append("intruder")
        self.assertNotIn("intruder", loc.connected_locations)

    def test_to_dict_matches_get_location_info(self):
        loc = make_location()
        self.assertEqual(loc.to_dict(), loc.get_location_info())

    def test_reset_location_clears_visit_state(self):
        loc = make_location()
        loc.visit()
        loc.visit()
        loc.reset_location()
        self.assertFalse(loc.is_visited())
        self.assertEqual(loc.visit_count, 0)

    def test_reset_location_preserves_connections_and_references(self):
        loc = make_location()
        loc.visit()
        loc.reset_location()
        self.assertEqual(loc.connected_locations, ["loc_b"])
        self.assertEqual(loc.available_evidence, ["evidence_a"])
        self.assertEqual(loc.available_clues, ["clue_a"])

    def test_from_dict_round_trip(self):
        loc = make_location()
        loc.visit()
        rebuilt = Location.from_dict(loc.to_dict())
        self.assertEqual(rebuilt.get_location_info(), loc.get_location_info())

    def test_from_dict_missing_field_raises(self):
        with self.assertRaises(KeyError):
            Location.from_dict({"location_id": "loc_a", "name": "n"})

    def test_repr_contains_key_fields(self):
        loc = make_location()
        text = repr(loc)
        self.assertIn("loc_a", text)
        self.assertIn("Drawing Room", text)


# -- LocationManager: registration & retrieval ---------------------------------

class TestLocationManagerRegistration(unittest.TestCase):
    def setUp(self):
        self.manager = LocationManager()

    def test_add_location_directly(self):
        loc = make_location()
        self.manager.add_location(loc)
        self.assertEqual(len(self.manager), 1)
        self.assertIs(self.manager.get_location("loc_a"), loc)

    def test_add_duplicate_location_id_raises(self):
        self.manager.add_location(make_location())
        with self.assertRaises(ValueError):
            self.manager.add_location(make_location())

    def test_add_wrong_type_raises(self):
        with self.assertRaises(TypeError):
            self.manager.add_location({"location_id": "loc_a"})

    def test_get_location_returns_none_when_missing(self):
        self.assertIsNone(self.manager.get_location("does_not_exist"))

    def test_get_all_locations(self):
        self.manager.add_location(make_location(location_id="loc_a"))
        self.manager.add_location(make_location(location_id="loc_b", connected_locations=[]))
        all_locations = self.manager.get_all_locations()
        self.assertEqual(len(all_locations), 2)

    def test_location_exists_true_and_false(self):
        self.manager.add_location(make_location())
        self.assertTrue(self.manager.location_exists("loc_a"))
        self.assertFalse(self.manager.location_exists("nope"))

    def test_remove_location_returns_true_and_removes(self):
        self.manager.add_location(make_location())
        removed = self.manager.remove_location("loc_a")
        self.assertTrue(removed)
        self.assertIsNone(self.manager.get_location("loc_a"))

    def test_remove_nonexistent_location_returns_false(self):
        self.assertFalse(self.manager.remove_location("nope"))

    def test_remove_location_cleans_up_dangling_connections(self):
        self.manager.add_location(make_location(location_id="loc_a", connected_locations=["loc_b"]))
        self.manager.add_location(make_location(location_id="loc_b", connected_locations=["loc_a"]))
        self.manager.remove_location("loc_a")
        remaining = self.manager.get_location("loc_b")
        self.assertNotIn("loc_a", remaining.connected_locations)

    def test_len_reflects_registered_count(self):
        self.assertEqual(len(self.manager), 0)
        self.manager.add_location(make_location())
        self.assertEqual(len(self.manager), 1)


# -- LocationManager: connecting locations --------------------------------------

class TestLocationManagerConnections(unittest.TestCase):
    def setUp(self):
        self.manager = LocationManager()
        self.manager.add_location(make_location(location_id="loc_a", connected_locations=[]))
        self.manager.add_location(make_location(location_id="loc_b", connected_locations=[]))

    def test_connect_locations_bidirectional_by_default(self):
        added = self.manager.connect_locations("loc_a", "loc_b")
        self.assertTrue(added)
        self.assertIn("loc_b", self.manager.get_location("loc_a").connected_locations)
        self.assertIn("loc_a", self.manager.get_location("loc_b").connected_locations)

    def test_connect_locations_one_directional(self):
        self.manager.connect_locations("loc_a", "loc_b", bidirectional=False)
        self.assertIn("loc_b", self.manager.get_location("loc_a").connected_locations)
        self.assertNotIn("loc_a", self.manager.get_location("loc_b").connected_locations)

    def test_connect_locations_duplicate_returns_false(self):
        self.manager.connect_locations("loc_a", "loc_b")
        added_again = self.manager.connect_locations("loc_a", "loc_b")
        self.assertFalse(added_again)
        # still only one connection each way, not two
        self.assertEqual(self.manager.get_location("loc_a").connected_locations.count("loc_b"), 1)

    def test_connect_locations_same_id_raises(self):
        with self.assertRaises(ValueError):
            self.manager.connect_locations("loc_a", "loc_a")

    def test_connect_locations_unknown_id_raises_keyerror(self):
        with self.assertRaises(KeyError):
            self.manager.connect_locations("loc_a", "does_not_exist")

    def test_connect_locations_unknown_first_id_raises_keyerror(self):
        with self.assertRaises(KeyError):
            self.manager.connect_locations("does_not_exist", "loc_b")


# -- LocationManager: JSON loading ----------------------------------------------

class TestLocationManagerJSONLoading(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp_path = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def _write_json(self, filename: str, data) -> Path:
        path = self.tmp_path / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f)
        return path

    def test_load_single_object_file(self):
        path = self._write_json(
            "single.json",
            {
                "location_id": "loc_a",
                "name": "Study",
                "description": "A quiet study.",
                "location_type": "room",
            },
        )
        manager = LocationManager()
        loaded = manager.load_location_from_file(path)
        self.assertEqual(len(loaded), 1)
        self.assertTrue(manager.location_exists("loc_a"))

    def test_load_list_of_objects_file(self):
        path = self._write_json(
            "many.json",
            [
                {
                    "location_id": "loc_a",
                    "name": "Study",
                    "description": "d",
                    "location_type": "room",
                },
                {
                    "location_id": "loc_b",
                    "name": "Hall",
                    "description": "d",
                    "location_type": "room",
                },
            ],
        )
        manager = LocationManager()
        loaded = manager.load_location_from_file(path)
        self.assertEqual(len(loaded), 2)
        self.assertTrue(manager.location_exists("loc_a"))
        self.assertTrue(manager.location_exists("loc_b"))

    def test_load_missing_file_records_error_and_returns_empty(self):
        manager = LocationManager()
        loaded = manager.load_location_from_file(self.tmp_path / "does_not_exist.json")
        self.assertEqual(loaded, [])
        self.assertTrue(manager.get_load_errors())

    def test_load_invalid_json_records_error(self):
        path = self.tmp_path / "broken.json"
        path.write_text("{ not valid json ][", encoding="utf-8")
        manager = LocationManager()
        loaded = manager.load_location_from_file(path)
        self.assertEqual(loaded, [])
        self.assertTrue(manager.get_load_errors())

    def test_load_skips_missing_required_fields(self):
        path = self._write_json(
            "incomplete.json",
            [
                {"location_id": "loc_a", "name": "Study"},  # missing fields
                {
                    "location_id": "loc_b",
                    "name": "Hall",
                    "description": "d",
                    "location_type": "room",
                },
            ],
        )
        manager = LocationManager()
        loaded = manager.load_location_from_file(path)
        self.assertEqual(len(loaded), 1)
        self.assertTrue(manager.location_exists("loc_b"))
        self.assertFalse(manager.location_exists("loc_a"))
        self.assertTrue(manager.get_load_errors())

    def test_load_skips_non_object_entries_in_list(self):
        path = self._write_json(
            "mixed.json",
            [
                "not an object",
                {
                    "location_id": "loc_b",
                    "name": "Hall",
                    "description": "d",
                    "location_type": "room",
                },
            ],
        )
        manager = LocationManager()
        loaded = manager.load_location_from_file(path)
        self.assertEqual(len(loaded), 1)
        self.assertTrue(manager.location_exists("loc_b"))

    def test_load_duplicate_location_id_across_files_records_error(self):
        self._write_json(
            "first.json",
            {
                "location_id": "loc_a",
                "name": "Study",
                "description": "d",
                "location_type": "room",
            },
        )
        self._write_json(
            "second.json",
            {
                "location_id": "loc_a",
                "name": "Study Again",
                "description": "d",
                "location_type": "room",
            },
        )
        manager = LocationManager()
        manager.load_all_locations(self.tmp_path)
        self.assertEqual(len(manager), 1)
        self.assertTrue(manager.get_load_errors())

    def test_load_all_locations_without_directory_raises(self):
        manager = LocationManager()
        with self.assertRaises(ValueError):
            manager.load_all_locations()

    def test_load_all_locations_missing_directory_records_error(self):
        manager = LocationManager()
        loaded = manager.load_all_locations(self.tmp_path / "nope")
        self.assertEqual(loaded, [])
        self.assertTrue(manager.get_load_errors())

    def test_load_all_locations_uses_default_directory(self):
        self._write_json(
            "single.json",
            {
                "location_id": "loc_a",
                "name": "Study",
                "description": "d",
                "location_type": "room",
            },
        )
        manager = LocationManager(locations_dir=self.tmp_path)
        loaded = manager.load_all_locations()
        self.assertEqual(len(loaded), 1)

    def test_load_real_case_001_location_data(self):
        """Loads the project's real cases/locations/case_001_locations.json
        to confirm the module integrates with the existing per-case JSON
        directory convention (mirroring evidence/clues/suspects)."""
        project_root = Path(__file__).resolve().parent.parent
        locations_file = project_root / "cases" / "locations" / "case_001_locations.json"
        manager = LocationManager()
        loaded = manager.load_location_from_file(locations_file)
        self.assertGreater(len(loaded), 0)
        self.assertEqual(manager.get_load_errors(), [])

        drawing_room = manager.get_location("loc_drawing_room")
        self.assertIsNotNone(drawing_room)
        self.assertIn("clue_silver_smell", drawing_room.get_available_clues())


if __name__ == "__main__":
    unittest.main()
