"""
Integration tests for the id-based Location system
(game/location.py) wired into Investigation (game/investigation.py)
and GameController (game/game_controller.py).

Unlike tests/test_location.py (pure Location/LocationManager unit
tests in isolation), these tests exercise the full chain:

    GameController -> Investigation -> LocationManager -> Location
        -> Evidence/Clue references -> EvidenceManager/ClueManager
        -> discovery tracking

Tests cover:
- Investigation constructed with a LocationManager exposes the
  id-based location methods; without one, they raise cleanly.
- GameController delegates location methods to Investigation without
  implementing any location business logic itself.
- Visiting locations, visit-count tracking, first-visit detection.
- Available evidence/clue ids surfaced per location (without
  auto-discovering them).
- Invalid location handling (unknown id, id not belonging to case).
- Case-specific location scoping (only the loaded case's locations
  are available).
- Current-location and visited-location tracking.
- Save/load of location state (visited/visit_count/current location),
  including backward compatibility with saves that predate location
  persistence.
- Achievement system compatibility: discovery/conclusion hooks still
  fire correctly once locations are wired in.

Run with:
    python -m unittest tests.test_location_integration
"""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from game.case import Case, CaseManager
from game.clue import Clue, ClueManager
from game.evidence import Evidence, EvidenceManager
from game.game_controller import GameController
from game.investigation import Investigation
from game.location import Location, LocationManager
from game.save_manager import SaveManager
from game.suspect import Suspect, SuspectManager


def make_case(**overrides) -> Case:
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
        locations=["loc_a", "loc_b"],
    )
    defaults.update(overrides)
    return Case(**defaults)


def make_evidence(**overrides) -> Evidence:
    defaults = dict(
        evidence_id="evidence_a",
        name="Test Evidence",
        description="Some evidence.",
        evidence_type="physical",
        location_found="Somewhere",
        importance="medium",
    )
    defaults.update(overrides)
    return Evidence(**defaults)


def make_clue(**overrides) -> Clue:
    defaults = dict(
        clue_id="clue_a",
        description="Some clue.",
        source="Inspection",
        location="Somewhere",
        importance="medium",
    )
    defaults.update(overrides)
    return Clue(**defaults)


def make_location(**overrides) -> Location:
    defaults = dict(
        location_id="loc_a",
        name="Location A",
        description="A place.",
        location_type="room",
        available_evidence=["evidence_a"],
        available_clues=["clue_a"],
    )
    defaults.update(overrides)
    return Location(**defaults)


def make_investigation_with_locations():
    """Build an Investigation wired with a LocationManager and one case."""
    case_manager = CaseManager()
    case = make_case()
    case_manager.add_case(case)

    evidence_manager = EvidenceManager()
    evidence_manager.add_evidence(make_evidence())
    evidence_manager.add_evidence(make_evidence(evidence_id="evidence_b"))

    clue_manager = ClueManager()
    clue_manager.add_clue(make_clue())

    suspect_manager = SuspectManager()
    suspect_manager.add_suspect(
        Suspect(
            suspect_id="suspect_a",
            name="Suspect A",
            age=30,
            occupation="Cook",
            description="A suspect for testing.",
            relationship_to_victim="Employee",
        )
    )
    suspect_manager.add_suspect(
        Suspect(
            suspect_id="suspect_b",
            name="Suspect B",
            age=40,
            occupation="Gardener",
            description="Another suspect for testing.",
            relationship_to_victim="Employee",
        )
    )

    location_manager = LocationManager()
    location_manager.add_location(make_location())
    location_manager.add_location(
        make_location(location_id="loc_b", name="Location B", available_evidence=[], available_clues=[])
    )

    investigation = Investigation(
        case_manager=case_manager,
        evidence_manager=evidence_manager,
        clue_manager=clue_manager,
        suspect_manager=suspect_manager,
        location_manager=location_manager,
    )
    investigation.start_investigation("case_test")
    return investigation, location_manager, case


# ---------------------------------------------------------------------------
# Investigation: id-based location methods
# ---------------------------------------------------------------------------


class TestInvestigationLocationManagerRequired(unittest.TestCase):
    def setUp(self):
        case_manager = CaseManager()
        case_manager.add_case(make_case())
        self.investigation = Investigation(
            case_manager=case_manager,
            evidence_manager=EvidenceManager(),
            clue_manager=ClueManager(),
            suspect_manager=SuspectManager(),
        )
        self.investigation.start_investigation("case_test")

    def test_get_available_locations_without_manager_raises(self):
        with self.assertRaises(RuntimeError):
            self.investigation.get_available_locations()

    def test_explore_location_by_id_without_manager_raises(self):
        with self.assertRaises(RuntimeError):
            self.investigation.explore_location_by_id("loc_a")

    def test_get_location_info_without_manager_raises(self):
        with self.assertRaises(RuntimeError):
            self.investigation.get_location_info("loc_a")

    def test_get_visited_location_ids_without_manager_returns_empty(self):
        # Read-only query -- gracefully empty rather than raising.
        self.assertEqual(self.investigation.get_visited_location_ids(), [])

    def test_free_text_inspect_location_still_works_without_manager(self):
        # Existing free-text model is entirely unaffected by the
        # optional LocationManager.
        result = self.investigation.inspect_location("Somewhere")
        self.assertIn("evidence_here", result)


class TestInvestigationAvailableLocations(unittest.TestCase):
    def setUp(self):
        self.investigation, self.location_manager, self.case = (
            make_investigation_with_locations()
        )

    def test_available_locations_scoped_to_case(self):
        locations = self.investigation.get_available_locations()
        ids = {loc.location_id for loc in locations}
        self.assertEqual(ids, {"loc_a", "loc_b"})

    def test_available_locations_excludes_locations_outside_case(self):
        self.location_manager.add_location(
            make_location(location_id="loc_outside", available_evidence=[], available_clues=[])
        )
        locations = self.investigation.get_available_locations()
        ids = {loc.location_id for loc in locations}
        self.assertNotIn("loc_outside", ids)


class TestInvestigationExploreLocationById(unittest.TestCase):
    def setUp(self):
        self.investigation, self.location_manager, self.case = (
            make_investigation_with_locations()
        )

    def test_first_visit_marks_visited_and_sets_visit_count(self):
        result = self.investigation.explore_location_by_id("loc_a")
        self.assertTrue(result["first_visit"])
        self.assertEqual(result["visit_count"], 1)

    def test_revisit_increments_visit_count_and_clears_first_visit(self):
        self.investigation.explore_location_by_id("loc_a")
        result = self.investigation.explore_location_by_id("loc_a")
        self.assertFalse(result["first_visit"])
        self.assertEqual(result["visit_count"], 2)

    def test_explore_sets_current_location(self):
        self.investigation.explore_location_by_id("loc_a")
        self.assertEqual(self.investigation.get_current_location_id(), "loc_a")
        self.investigation.explore_location_by_id("loc_b")
        self.assertEqual(self.investigation.get_current_location_id(), "loc_b")

    def test_explore_surfaces_available_evidence_and_clues(self):
        result = self.investigation.explore_location_by_id("loc_a")
        evidence_ids = {e["evidence_id"] for e in result["evidence_here"]}
        clue_ids = {c["clue_id"] for c in result["clues_here"]}
        self.assertIn("evidence_a", evidence_ids)
        self.assertIn("clue_a", clue_ids)

    def test_explore_does_not_auto_discover_evidence_or_clues(self):
        self.investigation.explore_location_by_id("loc_a")
        evidence = self.investigation.evidence_manager.get_evidence("evidence_a")
        clue = self.investigation.clue_manager.get_clue("clue_a")
        self.assertFalse(evidence.is_discovered())
        self.assertFalse(clue.is_discovered())

    def test_discovery_still_requires_explicit_discover_call(self):
        self.investigation.explore_location_by_id("loc_a")
        evidence = self.investigation.discover_evidence("evidence_a")
        self.assertTrue(evidence.is_discovered())

    def test_explore_unknown_location_id_raises_keyerror(self):
        with self.assertRaises(KeyError):
            self.investigation.explore_location_by_id("does_not_exist")

    def test_explore_location_not_belonging_to_case_raises_keyerror(self):
        self.location_manager.add_location(
            make_location(location_id="loc_outside", available_evidence=[], available_clues=[])
        )
        with self.assertRaises(KeyError):
            self.investigation.explore_location_by_id("loc_outside")

    def test_explore_empty_id_raises_valueerror(self):
        with self.assertRaises(ValueError):
            self.investigation.explore_location_by_id("")

    def test_explore_without_active_investigation_raises(self):
        investigation, _, _ = make_investigation_with_locations()
        investigation.end_investigation()
        with self.assertRaises(RuntimeError):
            investigation.explore_location_by_id("loc_a")


class TestInvestigationLocationInfo(unittest.TestCase):
    def setUp(self):
        self.investigation, self.location_manager, self.case = (
            make_investigation_with_locations()
        )

    def test_get_location_info_does_not_register_a_visit(self):
        self.investigation.get_location_info("loc_a")
        self.assertNotIn("loc_a", self.investigation.get_visited_location_ids())
        self.assertEqual(self.location_manager.get_location("loc_a").visit_count, 0)

    def test_get_location_info_includes_evidence_and_clues(self):
        info = self.investigation.get_location_info("loc_a")
        self.assertIn("evidence_here", info)
        self.assertIn("clues_here", info)

    def test_get_location_info_unknown_id_raises(self):
        with self.assertRaises(KeyError):
            self.investigation.get_location_info("nope")


class TestInvestigationVisitedLocationIds(unittest.TestCase):
    def setUp(self):
        self.investigation, self.location_manager, self.case = (
            make_investigation_with_locations()
        )

    def test_visited_ids_track_across_multiple_locations(self):
        self.investigation.explore_location_by_id("loc_a")
        self.investigation.explore_location_by_id("loc_b")
        self.assertEqual(
            set(self.investigation.get_visited_location_ids()), {"loc_a", "loc_b"}
        )

    def test_unvisited_locations_excluded(self):
        self.investigation.explore_location_by_id("loc_a")
        self.assertNotIn("loc_b", self.investigation.get_visited_location_ids())

    def test_visited_ids_sourced_from_location_not_duplicated_list(self):
        # Location itself is the single authoritative source -- directly
        # mutating a Location's visited flag should be reflected.
        self.location_manager.get_location("loc_b").visit()
        self.assertIn("loc_b", self.investigation.get_visited_location_ids())


class TestInvestigationLoadStateWithLocation(unittest.TestCase):
    def test_load_state_restores_current_location_id(self):
        investigation, _, case = make_investigation_with_locations()
        investigation.load_state(case, status="active", current_location_id="loc_b")
        self.assertEqual(investigation.get_current_location_id(), "loc_b")

    def test_load_state_defaults_current_location_id_to_none(self):
        investigation, _, case = make_investigation_with_locations()
        investigation.load_state(case, status="active")
        self.assertIsNone(investigation.get_current_location_id())


# ---------------------------------------------------------------------------
# GameController delegation
# ---------------------------------------------------------------------------


class TestGameControllerLocationDelegation(unittest.TestCase):
    def setUp(self):
        self.saves_dir = tempfile.mkdtemp()
        self.controller = GameController("p1", "Ada Detective", saves_dir=self.saves_dir)
        self.controller.load_case("case_001")
        self.controller.start_investigation()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.saves_dir, ignore_errors=True)

    def test_investigation_has_location_manager_wired(self):
        self.assertIs(
            self.controller.investigation.location_manager, self.controller.location_manager
        )

    def test_get_available_locations_delegates_to_investigation(self):
        locations = self.controller.get_available_locations()
        self.assertGreater(len(locations), 0)
        self.assertTrue(all(isinstance(loc, Location) for loc in locations))

    def test_explore_location_by_id_delegates_and_visits(self):
        location_id = self.controller.get_available_locations()[0].location_id
        result = self.controller.explore_location_by_id(location_id)
        self.assertTrue(result["first_visit"])
        self.assertIn(location_id, self.controller.get_visited_location_ids())

    def test_get_location_info_delegates(self):
        location_id = self.controller.get_available_locations()[0].location_id
        info = self.controller.get_location_info(location_id)
        self.assertEqual(info["location_id"], location_id)

    def test_get_current_location_id_delegates(self):
        location_id = self.controller.get_available_locations()[0].location_id
        self.assertIsNone(self.controller.get_current_location_id())
        self.controller.explore_location_by_id(location_id)
        self.assertEqual(self.controller.get_current_location_id(), location_id)

    def test_get_visited_location_ids_delegates(self):
        self.assertEqual(self.controller.get_visited_location_ids(), [])
        location_id = self.controller.get_available_locations()[0].location_id
        self.controller.explore_location_by_id(location_id)
        self.assertEqual(self.controller.get_visited_location_ids(), [location_id])

    def test_free_text_explore_location_still_works(self):
        # The pre-existing free-text location model must be completely
        # unaffected by the new id-based delegation methods.
        locations = self.controller.get_case_locations()
        self.assertGreater(len(locations), 0)
        result = self.controller.explore_location(locations[0])
        self.assertIn("evidence_here", result)

    def test_gamecontroller_has_no_location_business_logic(self):
        # GameController's location methods should be pure one-line
        # delegations -- verified indirectly: exploring an unknown id
        # raises the same KeyError Investigation itself raises, not a
        # GameController-specific error.
        with self.assertRaises(KeyError):
            self.controller.explore_location_by_id("does_not_exist_at_all")

    def test_explore_location_by_id_without_investigation_raises(self):
        controller = GameController("p2", "Bob", saves_dir=self.saves_dir)
        with self.assertRaises(RuntimeError):
            controller.get_available_locations()


class TestGameControllerCaseScopedLocations(unittest.TestCase):
    def setUp(self):
        self.saves_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.saves_dir, ignore_errors=True)

    def test_locations_loaded_and_linked_to_case_on_load(self):
        controller = GameController("p1", "Ada", saves_dir=self.saves_dir)
        case = controller.load_case("case_001")
        self.assertGreater(len(case.locations), 0)
        for location_id in case.locations:
            self.assertTrue(controller.location_manager.location_exists(location_id))


# ---------------------------------------------------------------------------
# Save / load integration
# ---------------------------------------------------------------------------


class TestLocationSaveLoadIntegration(unittest.TestCase):
    def setUp(self):
        self.saves_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.saves_dir, ignore_errors=True)

    def test_save_and_load_restores_visit_state(self):
        controller = GameController("p1", "Ada", saves_dir=self.saves_dir)
        controller.load_case("case_001")
        controller.start_investigation()

        location_id = controller.get_available_locations()[0].location_id
        controller.explore_location_by_id(location_id)
        controller.explore_location_by_id(location_id)  # visit_count -> 2

        self.assertTrue(controller.save_game("slot_1"))

        reloaded = GameController("p1", "Ada", saves_dir=self.saves_dir)
        self.assertTrue(reloaded.load_game("slot_1"))

        restored = reloaded.location_manager.get_location(location_id)
        self.assertTrue(restored.visited)
        self.assertEqual(restored.visit_count, 2)

    def test_save_and_load_restores_current_location(self):
        controller = GameController("p1", "Ada", saves_dir=self.saves_dir)
        controller.load_case("case_001")
        controller.start_investigation()

        location_id = controller.get_available_locations()[0].location_id
        controller.explore_location_by_id(location_id)
        controller.save_game("slot_2")

        reloaded = GameController("p1", "Ada", saves_dir=self.saves_dir)
        reloaded.load_game("slot_2")

        self.assertEqual(reloaded.get_current_location_id(), location_id)

    def test_save_and_load_restores_visited_ids(self):
        controller = GameController("p1", "Ada", saves_dir=self.saves_dir)
        controller.load_case("case_001")
        controller.start_investigation()

        locations = controller.get_available_locations()
        controller.explore_location_by_id(locations[0].location_id)
        controller.explore_location_by_id(locations[1].location_id)
        controller.save_game("slot_3")

        reloaded = GameController("p1", "Ada", saves_dir=self.saves_dir)
        reloaded.load_game("slot_3")

        self.assertEqual(
            set(reloaded.get_visited_location_ids()),
            {locations[0].location_id, locations[1].location_id},
        )

    def test_backward_compatible_load_without_location_data(self):
        controller = GameController("p1", "Ada", saves_dir=self.saves_dir)
        controller.load_case("case_001")
        controller.start_investigation()
        location_id = controller.get_available_locations()[0].location_id
        controller.explore_location_by_id(location_id)

        # Save via a bare SaveManager call, omitting location_manager --
        # simulates a save written before location persistence existed.
        save_manager = SaveManager(saves_dir=self.saves_dir, case_manager=controller.case_manager)
        ok = save_manager.save_game(
            controller.game_state,
            slot_name="legacy_slot",
            evidence_manager=controller.evidence_manager,
            clue_manager=controller.clue_manager,
            suspect_manager=controller.suspect_manager,
            investigation=controller.investigation,
            achievement_manager=controller.achievement_manager,
        )
        self.assertTrue(ok)

        reloaded = GameController("p1", "Ada", saves_dir=self.saves_dir)
        self.assertTrue(reloaded.load_game("legacy_slot"))

        # Locations still load fresh from case data (unvisited), and
        # nothing raises despite the absence of "location_data".
        self.assertGreater(len(reloaded.get_available_locations()), 0)
        restored = reloaded.location_manager.get_location(location_id)
        self.assertFalse(restored.visited)
        self.assertEqual(restored.visit_count, 0)

    def test_load_investigation_state_includes_current_location_id_key(self):
        controller = GameController("p1", "Ada", saves_dir=self.saves_dir)
        controller.load_case("case_001")
        controller.start_investigation()
        location_id = controller.get_available_locations()[0].location_id
        controller.explore_location_by_id(location_id)
        controller.save_game("slot_4")

        inv_state = controller.save_manager.load_investigation_state("slot_4")
        self.assertEqual(inv_state["current_location_id"], location_id)

    def test_ancient_save_with_no_investigation_context_still_loads(self):
        # Simulates a save from before Investigation-level persistence
        # existed at all: only game_state, nothing else.
        controller = GameController("p1", "Ada", saves_dir=self.saves_dir)
        controller.load_case("case_001")
        controller.start_investigation()

        save_manager = SaveManager(saves_dir=self.saves_dir, case_manager=controller.case_manager)
        self.assertTrue(save_manager.save_game(controller.game_state, slot_name="ancient"))

        reloaded = GameController("p1", "Ada", saves_dir=self.saves_dir)
        self.assertTrue(reloaded.load_game("ancient"))
        self.assertGreater(len(reloaded.get_available_locations()), 0)
        self.assertIsNone(reloaded.get_current_location_id())


# ---------------------------------------------------------------------------
# Achievement compatibility
# ---------------------------------------------------------------------------


class TestLocationAchievementCompatibility(unittest.TestCase):
    def setUp(self):
        self.saves_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil

        shutil.rmtree(self.saves_dir, ignore_errors=True)

    def test_discover_evidence_via_location_flow_still_triggers_achievements(self):
        controller = GameController("p1", "Ada", saves_dir=self.saves_dir)
        controller.load_case("case_001")
        controller.start_investigation()

        for location in controller.get_available_locations():
            result = controller.explore_location_by_id(location.location_id)
            for evidence_info in result["evidence_here"]:
                if not evidence_info["discovered"]:
                    controller.discover_evidence(evidence_info["evidence_id"])
            for clue_info in result["clues_here"]:
                if not clue_info["discovered"]:
                    controller.discover_clue(clue_info["clue_id"])

        unlocked_ids = {a.achievement_id for a in controller.get_unlocked_achievements()}
        self.assertIn("evidence_hunter", unlocked_ids)
        self.assertIn("clue_collector", unlocked_ids)

    def test_conclude_case_after_location_exploration_still_unlocks_first_case(self):
        controller = GameController("p1", "Ada", saves_dir=self.saves_dir)
        controller.load_case("case_001")
        controller.start_investigation()

        for location in controller.get_available_locations():
            controller.explore_location_by_id(location.location_id)

        outcome = controller.conclude_case(controller.case.correct_suspect)
        self.assertIn("first_case", outcome["achievements_unlocked"])

    def test_achievement_state_and_location_state_both_survive_save_load(self):
        controller = GameController("p1", "Ada", saves_dir=self.saves_dir)
        controller.load_case("case_001")
        controller.start_investigation()

        for location in controller.get_available_locations():
            result = controller.explore_location_by_id(location.location_id)
            for evidence_info in result["evidence_here"]:
                if not evidence_info["discovered"]:
                    controller.discover_evidence(evidence_info["evidence_id"])
            for clue_info in result["clues_here"]:
                if not clue_info["discovered"]:
                    controller.discover_clue(clue_info["clue_id"])

        controller.conclude_case(controller.case.correct_suspect)

        unlocked_before = sorted(
            a.achievement_id for a in controller.get_unlocked_achievements()
        )
        visited_before = set(controller.get_visited_location_ids())

        controller.save_game("combo_slot")

        reloaded = GameController("p1", "Ada", saves_dir=self.saves_dir)
        reloaded.load_game("combo_slot")

        unlocked_after = sorted(
            a.achievement_id for a in reloaded.get_unlocked_achievements()
        )
        self.assertEqual(unlocked_before, unlocked_after)

        visited_after = set(
            loc.location_id
            for loc in reloaded.location_manager.get_all_locations()
            if loc.is_visited() and loc.location_id in reloaded.case.locations
        )
        self.assertEqual(visited_before, visited_after)


if __name__ == "__main__":
    unittest.main()
