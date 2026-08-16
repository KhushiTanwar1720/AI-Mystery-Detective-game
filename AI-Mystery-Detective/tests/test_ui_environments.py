"""
Unit tests for ui/environments.py -- the data-driven location-to-
environment resolver and EnvironmentSpec registry backing the
location-aware visual atmosphere system.

Deliberately does NOT import pygame or ui.environment_renderer;
ui.environments is designed to be pygame-free and independently
testable (same pattern as ui.campaign).

Run with:
    python -m unittest tests.test_ui_environments
"""

import glob
import json
import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ui.environments import (
    ABANDONED_BUILDING,
    ASYLUM,
    BASEMENT,
    BEDROOM,
    DRAWING_ROOM,
    ENVIRONMENTS,
    FINAL_CASE,
    FOREST,
    GARDEN,
    GENERIC_INTERIOR,
    HOSPITAL,
    KITCHEN,
    LABORATORY,
    LIGHTHOUSE,
    MANSION_INTERIOR,
    RENDER_FINAL,
    RENDER_INTERIOR,
    RENDER_OUTDOOR,
    RENDER_UNDERGROUND,
    SCHOOL,
    UNDERGROUND_FACILITY,
    UNDERGROUND_STATION,
    VILLAGE,
    EnvironmentSpec,
    resolve_environment,
    spec_for,
    stable_seed,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CASES_DIR = PROJECT_ROOT / "cases"


class TestNoPygameDependency(unittest.TestCase):
    def test_environments_module_source_never_imports_pygame(self):
        import ui.environments as environments_module

        source = Path(environments_module.__file__).read_text()
        import_lines = [
            line.strip() for line in source.splitlines()
            if line.strip().startswith("import ") or line.strip().startswith("from ")
        ]
        self.assertTrue(all("pygame" not in line for line in import_lines))


class TestEnvironmentRegistry(unittest.TestCase):
    def test_every_environment_has_a_spec(self):
        for environment_id in (
            MANSION_INTERIOR, BEDROOM, DRAWING_ROOM, KITCHEN, GARDEN, FOREST,
            BASEMENT, ABANDONED_BUILDING, SCHOOL, HOSPITAL, ASYLUM,
            UNDERGROUND_STATION, VILLAGE, LIGHTHOUSE, LABORATORY,
            UNDERGROUND_FACILITY, FINAL_CASE, GENERIC_INTERIOR,
        ):
            self.assertIn(environment_id, ENVIRONMENTS)
            self.assertIsInstance(ENVIRONMENTS[environment_id], EnvironmentSpec)

    def test_every_spec_uses_a_known_renderer(self):
        valid_renderers = {RENDER_INTERIOR, RENDER_OUTDOOR, RENDER_UNDERGROUND, RENDER_FINAL}
        for environment_id, spec in ENVIRONMENTS.items():
            with self.subTest(environment_id=environment_id):
                self.assertIn(spec.renderer, valid_renderers)

    def test_every_spec_has_at_least_one_decoration(self):
        for environment_id, spec in ENVIRONMENTS.items():
            with self.subTest(environment_id=environment_id):
                self.assertGreater(len(spec.decorations), 0)

    def test_colors_are_valid_rgb_tuples(self):
        for environment_id, spec in ENVIRONMENTS.items():
            for color in (spec.top_color, spec.bottom_color, spec.floor_color, spec.accent_color):
                with self.subTest(environment_id=environment_id, color=color):
                    self.assertEqual(len(color), 3)
                    self.assertTrue(all(0 <= c <= 255 for c in color))

    def test_final_case_has_the_strongest_fog_boost(self):
        final_fog = ENVIRONMENTS[FINAL_CASE].fog_boost
        for environment_id, spec in ENVIRONMENTS.items():
            if environment_id != FINAL_CASE:
                with self.subTest(environment_id=environment_id):
                    self.assertGreaterEqual(final_fog, spec.fog_boost)

    def test_drawing_room_and_kitchen_are_visually_distinct(self):
        # The two calmest, least-fog level-1 environments must still
        # not collapse into identical colors.
        drawing = ENVIRONMENTS[DRAWING_ROOM]
        kitchen = ENVIRONMENTS[KITCHEN]
        self.assertNotEqual(drawing.top_color, kitchen.top_color)
        self.assertNotEqual(drawing.decorations, kitchen.decorations)

    def test_spec_for_unknown_id_falls_back_to_generic_interior(self):
        self.assertIs(spec_for("not_a_real_environment"), ENVIRONMENTS[GENERIC_INTERIOR])

    def test_spec_for_known_id_returns_that_spec(self):
        self.assertIs(spec_for(FOREST), ENVIRONMENTS[FOREST])

    def test_every_decoration_name_is_registered_in_the_renderer(self):
        # ui.environment_renderer requires pygame to import, so this
        # check parses its source text for the DECORATION_DRAWERS
        # registry rather than importing it -- keeping this test
        # (and the module under test here) pygame-free, while still
        # catching a spec referencing a decoration name the renderer
        # never registered (a real bug this test caught once already:
        # "barred_window" vs the registered "window_barred").
        import re

        renderer_path = Path(__file__).resolve().parent.parent / "ui" / "environment_renderer.py"
        source = renderer_path.read_text()
        registered = set(re.findall(r'"(\w+)":\s*_draw_\w+,', source))
        self.assertGreater(len(registered), 0, "failed to parse any registered decorations")

        missing = []
        for environment_id, spec in ENVIRONMENTS.items():
            for decoration in spec.decorations:
                if decoration not in registered:
                    missing.append((environment_id, decoration))
        self.assertEqual(missing, [])


class TestResolveEnvironmentByName(unittest.TestCase):
    def test_kitchen(self):
        self.assertEqual(resolve_environment("Kitchen"), KITCHEN)
        self.assertEqual(resolve_environment("Kitchen Hallway"), KITCHEN)

    def test_garden(self):
        self.assertEqual(resolve_environment("Garden"), GARDEN)
        self.assertEqual(resolve_environment("Garden Path"), GARDEN)

    def test_drawing_room(self):
        self.assertEqual(resolve_environment("Drawing Room"), DRAWING_ROOM)

    def test_lighthouse(self):
        self.assertEqual(resolve_environment("Lighthouse Entrance"), LIGHTHOUSE)
        self.assertEqual(resolve_environment("Lantern Room"), LIGHTHOUSE)
        self.assertEqual(resolve_environment("Keeper's Room"), LIGHTHOUSE)

    def test_hospital(self):
        self.assertEqual(resolve_environment("Patient Ward"), HOSPITAL)
        self.assertEqual(resolve_environment("Operating Wing"), HOSPITAL)

    def test_asylum(self):
        self.assertEqual(resolve_environment("Treatment Wing"), ASYLUM)

    def test_forest(self):
        self.assertEqual(resolve_environment("Forest Trail"), FOREST)
        self.assertEqual(resolve_environment("Ranger Cabin"), FOREST)
        self.assertEqual(resolve_environment("Watchtower"), FOREST)

    def test_village(self):
        self.assertEqual(resolve_environment("Village Square"), VILLAGE)
        self.assertEqual(resolve_environment("Abandoned Church"), VILLAGE)

    def test_school(self):
        self.assertEqual(resolve_environment("Classroom Wing"), SCHOOL)
        self.assertEqual(resolve_environment("Old Auditorium"), SCHOOL)

    def test_laboratory(self):
        self.assertEqual(resolve_environment("Laboratory"), LABORATORY)
        self.assertEqual(resolve_environment("Server Room"), LABORATORY)

    def test_underground_station(self):
        self.assertEqual(resolve_environment("Platform"), UNDERGROUND_STATION)
        self.assertEqual(resolve_environment("Maintenance Tunnel"), UNDERGROUND_STATION)

    def test_basement_always_wins_regardless_of_case(self):
        self.assertEqual(resolve_environment("Basement", case_title="The Missing Necklace"), BASEMENT)
        self.assertEqual(resolve_environment("Basement", case_title="The Silent Hospital"), BASEMENT)
        self.assertEqual(resolve_environment("Basement", case_title="The Lighthouse"), BASEMENT)

    def test_bedroom_covers_attic(self):
        self.assertEqual(resolve_environment("Attic"), BEDROOM)

    def test_abandoned_building_for_hotel_rooms(self):
        self.assertEqual(resolve_environment("Room 207"), ABANDONED_BUILDING)
        self.assertEqual(resolve_environment("Guest Hallway"), ABANDONED_BUILDING)

    def test_unknown_name_falls_back_to_generic_interior(self):
        self.assertEqual(resolve_environment("Something Never Seen Before"), GENERIC_INTERIOR)

    def test_empty_name_does_not_crash(self):
        self.assertEqual(resolve_environment(""), GENERIC_INTERIOR)
        self.assertEqual(resolve_environment(None), GENERIC_INTERIOR)  # type: ignore[arg-type]


class TestResolveEnvironmentByCaseTitleFallback(unittest.TestCase):
    def test_generic_room_name_falls_back_to_case_title(self):
        self.assertEqual(resolve_environment("Main Hall", case_title="The Forgotten Asylum"), ASYLUM)
        self.assertEqual(resolve_environment("Observation Room", case_title="The Forgotten Asylum"), ASYLUM)
        self.assertEqual(resolve_environment("Archive", case_title="The Forgotten Asylum"), ASYLUM)

    def test_manor_case_title_fallback(self):
        self.assertEqual(resolve_environment("Hidden Corridor", case_title="The Manor Beneath the Fog"), MANSION_INTERIOR)

    def test_research_facility_case_title_fallback(self):
        self.assertEqual(
            resolve_environment("Observation Room", case_title="The Frozen Research Facility"), LABORATORY
        )

    def test_no_case_title_and_no_name_match_falls_back_to_generic(self):
        self.assertEqual(resolve_environment("Main Hall"), GENERIC_INTERIOR)


class TestFinalCaseOverride(unittest.TestCase):
    def test_any_location_in_the_final_case_resolves_to_final_case(self):
        for name in ("Detective's Office", "Blackwood Mansion Ruins", "The Society's Chamber", "Random Room"):
            with self.subTest(name=name):
                self.assertEqual(resolve_environment(name, case_title="THE FINAL CASE"), FINAL_CASE)

    def test_final_case_override_beats_name_keywords(self):
        # Even a name that would normally resolve elsewhere (e.g.
        # "Kitchen") is overridden by the finale's case-title marker.
        self.assertEqual(resolve_environment("Kitchen", case_title="THE FINAL CASE"), FINAL_CASE)


class TestStableSeed(unittest.TestCase):
    def test_same_location_id_always_same_seed(self):
        self.assertEqual(stable_seed("loc_drawing_room"), stable_seed("loc_drawing_room"))

    def test_different_location_ids_usually_differ(self):
        self.assertNotEqual(stable_seed("loc_drawing_room"), stable_seed("loc_kitchen"))

    def test_seed_is_a_small_nonnegative_int(self):
        seed = stable_seed("loc_some_very_long_location_identifier_string")
        self.assertIsInstance(seed, int)
        self.assertGreaterEqual(seed, 0)
        self.assertLess(seed, 9973)


class TestAgainstRealCampaignData(unittest.TestCase):
    """Resolve every location in every real campaign case file and
    confirm nothing falls through to a nonsensical result -- this is
    the actual data the game ships with, not synthetic examples.
    """

    def _all_case_titles(self):
        titles = {}
        for path in sorted(glob.glob(str(CASES_DIR / "case_*.json"))):
            data = json.loads(Path(path).read_text())
            titles[data["case_id"]] = data["title"]
        return titles

    def test_every_campaign_location_resolves_to_a_registered_environment(self):
        titles = self._all_case_titles()
        location_files = sorted(glob.glob(str(CASES_DIR / "locations" / "*_locations.json")))
        self.assertGreater(len(location_files), 0)

        for path in location_files:
            case_id = Path(path).name.replace("_locations.json", "")
            title = titles.get(case_id, "")
            locations = json.loads(Path(path).read_text())
            for location in locations:
                environment_id = resolve_environment(location["name"], title)
                with self.subTest(case_id=case_id, location=location["name"]):
                    self.assertIn(environment_id, ENVIRONMENTS)

    def test_final_case_level_locations_all_resolve_to_final_case(self):
        titles = self._all_case_titles()
        final_case_id = next((cid for cid, title in titles.items() if "final case" in title.lower()), None)
        self.assertIsNotNone(final_case_id, "expected a campaign case titled containing 'final case'")

        location_path = CASES_DIR / "locations" / f"{final_case_id}_locations.json"
        locations = json.loads(location_path.read_text())
        self.assertGreater(len(locations), 0)
        for location in locations:
            with self.subTest(location=location["name"]):
                self.assertEqual(resolve_environment(location["name"], titles[final_case_id]), FINAL_CASE)

    def test_level_one_locations_are_not_all_identical_environments(self):
        # Direct regression check for the original complaint: level 1
        # locations must not all collapse onto one environment.
        titles = self._all_case_titles()
        level_one_id = next(
            (cid for cid, title in titles.items() if "missing necklace" in title.lower()), None
        )
        self.assertIsNotNone(level_one_id)

        location_path = CASES_DIR / "locations" / f"{level_one_id}_locations.json"
        locations = json.loads(location_path.read_text())
        environments = {resolve_environment(loc["name"], titles[level_one_id]) for loc in locations}
        self.assertGreater(len(environments), 1)


if __name__ == "__main__":
    unittest.main()
