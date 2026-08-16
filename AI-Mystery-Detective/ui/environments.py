"""
Location-aware visual environment system (data layer).

This module has two jobs, and is intentionally free of any
`import pygame` so it can be loaded and unit-tested without pygame
installed (same pattern as `ui.campaign`):

1. `resolve_environment(...)` -- decide *which* environment identity
   (mansion interior, kitchen, garden, forest, hospital, asylum,
   lighthouse, laboratory, underground facility, final case, ...) a
   given location belongs to, purely from data already on the
   `Location`/`Case` objects (name, case title) -- no new backend
   fields, no hardcoded per-screen mapping. The same location always
   resolves to the same environment (pure function of its inputs), so
   its visual identity is stable across visits (requirement: "the
   same location should always have a consistent visual identity").

2. `ENVIRONMENTS` -- a registry of `EnvironmentSpec` describing each
   environment's palette and decorative silhouette set. The actual
   pygame drawing lives in `ui.environment_renderer`, which reads
   these specs rather than hardcoding colors per screen -- adding a
   new environment means adding one `EnvironmentSpec` entry, not
   writing new screen code.

Horror-tier intensity (fog/vignette/flicker) is layered on top of an
environment's own `fog_boost` by `ui.theme.palette_for` /
`ui.environment_renderer` -- environment identity and horror
intensity are two independent, orthogonal dials, exactly as the
brief asks for ("progressively increase" horror while locations stay
"meaningfully different" from each other).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Sequence, Tuple

Color = Tuple[int, int, int]

# -- Environment identities ---------------------------------------------------

MANSION_INTERIOR = "mansion_interior"
BEDROOM = "bedroom"
DRAWING_ROOM = "drawing_room"
KITCHEN = "kitchen"
GARDEN = "garden"
FOREST = "forest"
BASEMENT = "basement"
ABANDONED_BUILDING = "abandoned_building"
SCHOOL = "school"
HOSPITAL = "hospital"
ASYLUM = "asylum"
UNDERGROUND_STATION = "underground_station"
VILLAGE = "village"
LIGHTHOUSE = "lighthouse"
LABORATORY = "laboratory"
UNDERGROUND_FACILITY = "underground_facility"
FINAL_CASE = "final_case"
GENERIC_INTERIOR = "generic_interior"

# Rendering strategy each environment uses -- `ui.environment_renderer`
# dispatches on this rather than one bespoke function per environment.
RENDER_INTERIOR = "interior"
RENDER_OUTDOOR = "outdoor"
RENDER_UNDERGROUND = "underground"
RENDER_FINAL = "final"


@dataclass(frozen=True)
class EnvironmentSpec:
    """Visual identity for one environment kind.

    Attributes:
        renderer: One of the `RENDER_*` strategy constants, dispatched
            on by `ui.environment_renderer`.
        top_color / bottom_color: Gradient endpoints for the main
            backdrop (sky for outdoor, upper/lower wall for interior,
            tunnel-mouth-to-depth for underground).
        floor_color: Ground/floor band color.
        accent_color: Small highlight color (window glow, lantern,
            warning light, etc.) -- distinct per environment so even
            two dim rooms read differently.
        decorations: Names of silhouette elements to draw (see
            `ui.environment_renderer.DECORATION_DRAWERS`), determining
            each environment's distinct layout/furniture identity.
        fog_boost: Extra 0..1 fog contribution this environment always
            carries, on top of the level's horror-tier fog (e.g. a
            lighthouse in a storm is foggier than a sunlit drawing
            room even at the same horror tier).
    """

    renderer: str
    top_color: Color
    bottom_color: Color
    floor_color: Color
    accent_color: Color
    decorations: Tuple[str, ...] = field(default_factory=tuple)
    fog_boost: float = 0.0


ENVIRONMENTS: Dict[str, EnvironmentSpec] = {
    MANSION_INTERIOR: EnvironmentSpec(
        RENDER_INTERIOR, (34, 28, 26), (14, 11, 11), (22, 18, 16), (196, 160, 80),
        decorations=("pillar", "chandelier_large", "portrait_frame", "drape"),
        fog_boost=0.10,
    ),
    BEDROOM: EnvironmentSpec(
        RENDER_INTERIOR, (40, 32, 36), (16, 12, 14), (28, 22, 22), (170, 140, 150),
        decorations=("bed_frame", "window_small", "dresser", "cobweb"),
        fog_boost=0.15,
    ),
    DRAWING_ROOM: EnvironmentSpec(
        RENDER_INTERIOR, (50, 40, 32), (20, 16, 12), (34, 27, 20), (196, 160, 80),
        decorations=("window_arched", "chandelier", "armchair", "fireplace"),
        fog_boost=0.0,
    ),
    KITCHEN: EnvironmentSpec(
        RENDER_INTERIOR, (58, 50, 42), (26, 22, 18), (40, 35, 28), (200, 150, 90),
        decorations=("counter", "cabinet", "window_small", "hanging_pot"),
        fog_boost=0.0,
    ),
    GARDEN: EnvironmentSpec(
        RENDER_OUTDOOR, (22, 26, 32), (9, 11, 15), (18, 26, 16), (120, 150, 100),
        decorations=("hedge", "fountain", "tree_small", "fence"),
        fog_boost=0.10,
    ),
    FOREST: EnvironmentSpec(
        RENDER_OUTDOOR, (11, 13, 19), (4, 5, 8), (12, 16, 10), (95, 115, 85),
        decorations=("tree_tall", "tree_tall", "tree_small", "cabin_silhouette"),
        fog_boost=0.40,
    ),
    BASEMENT: EnvironmentSpec(
        RENDER_UNDERGROUND, (16, 15, 15), (5, 5, 5), (12, 11, 11), (180, 150, 70),
        decorations=("pipes_thin", "support_beam", "bare_bulb", "crate"),
        fog_boost=0.30,
    ),
    ABANDONED_BUILDING: EnvironmentSpec(
        RENDER_INTERIOR, (34, 30, 32), (13, 11, 13), (24, 20, 20), (150, 120, 110),
        decorations=("peeling_wallpaper", "reception_desk", "broken_light", "door_row"),
        fog_boost=0.30,
    ),
    SCHOOL: EnvironmentSpec(
        RENDER_INTERIOR, (30, 32, 34), (11, 12, 14), (20, 22, 24), (120, 150, 170),
        decorations=("lockers", "chalkboard", "desk_row", "window_barred"),
        fog_boost=0.20,
    ),
    HOSPITAL: EnvironmentSpec(
        RENDER_INTERIOR, (24, 30, 30), (9, 12, 12), (17, 22, 22), (120, 180, 170),
        decorations=("hospital_bed", "curtain_divider", "monitor_stand", "flicker_light"),
        fog_boost=0.35,
    ),
    ASYLUM: EnvironmentSpec(
        RENDER_INTERIOR, (20, 18, 20), (7, 6, 7), (15, 13, 15), (150, 60, 60),
        decorations=("restraint_chair", "window_barred", "door_heavy", "stain"),
        fog_boost=0.45,
    ),
    UNDERGROUND_STATION: EnvironmentSpec(
        RENDER_UNDERGROUND, (17, 19, 22), (6, 7, 9), (13, 14, 16), (90, 130, 150),
        decorations=("platform_edge", "pillar_tiled", "sign_faded", "tracks"),
        fog_boost=0.40,
    ),
    VILLAGE: EnvironmentSpec(
        RENDER_OUTDOOR, (13, 13, 17), (5, 5, 7), (16, 16, 14), (140, 110, 90),
        decorations=("house_silhouette", "church_spire", "well_stone", "fence_broken"),
        fog_boost=0.45,
    ),
    LIGHTHOUSE: EnvironmentSpec(
        RENDER_INTERIOR, (14, 18, 26), (5, 7, 11), (12, 16, 22), (150, 190, 210),
        decorations=("spiral_stairs", "window_round", "lantern_glow", "storm_streaks"),
        fog_boost=0.35,
    ),
    LABORATORY: EnvironmentSpec(
        RENDER_INTERIOR, (15, 19, 21), (5, 7, 8), (13, 16, 17), (90, 190, 200),
        decorations=("server_rack", "monitor_bank", "pipes_metal", "warning_light"),
        fog_boost=0.45,
    ),
    UNDERGROUND_FACILITY: EnvironmentSpec(
        RENDER_UNDERGROUND, (13, 11, 13), (4, 4, 5), (10, 9, 10), (170, 60, 50),
        decorations=("pipes_thick", "support_beam", "warning_tape", "flicker_light"),
        fog_boost=0.55,
    ),
    FINAL_CASE: EnvironmentSpec(
        RENDER_FINAL, (10, 5, 6), (2, 1, 2), (8, 4, 5), (170, 40, 40),
        decorations=("chamber_pillars", "candle_ring", "shattered_glass", "eye_glow"),
        fog_boost=0.80,
    ),
    GENERIC_INTERIOR: EnvironmentSpec(
        RENDER_INTERIOR, (26, 24, 26), (11, 10, 11), (20, 18, 20), (196, 160, 80),
        decorations=("desk", "filing_cabinet", "window_small", "lamp"),
        fog_boost=0.10,
    ),
}

# -- Resolution ---------------------------------------------------------------

# Checked against the location's own name first (most specific/reliable
# signal). Order matters: earlier entries win on a tie, so more
# specific phrases are listed before broader ones.
_NAME_KEYWORDS: Sequence[Tuple[str, Sequence[str]]] = (
    (LIGHTHOUSE, ("lighthouse", "lantern room", "keeper's room", "spiral staircase")),
    (LABORATORY, ("laboratory", " lab", "server room")),
    (BASEMENT, ("basement",)),
    (HOSPITAL, ("patient ward", "operating wing", "records room")),
    (ASYLUM, ("treatment wing", "asylum")),
    (UNDERGROUND_STATION, ("platform", "maintenance tunnel", "station entrance", "control room", "restricted office", "tracks")),
    (VILLAGE, ("village square", "church", "well area", "flooded street", "town hall")),
    (FOREST, ("forest trail", "forest path", "ranger cabin", "watchtower", "abandoned camp", "trail")),
    (SCHOOL, ("classroom", "principal's office", "old auditorium", "school entrance")),
    (ABANDONED_BUILDING, ("hotel", "guest hallway", "room 207", "old house", "abandoned house")),
    (BEDROOM, ("attic", "bedroom", "guest room")),
    (KITCHEN, ("kitchen",)),
    (GARDEN, ("garden",)),
    (DRAWING_ROOM, ("drawing room",)),
    (MANSION_INTERIOR, ("ballroom", "servant quarters", "manor entrance", "hidden corridor", "front hall", "library")),
)

# Fallback: checked against the *case title* when the location's own
# name gives no strong signal (e.g. "Main Hall", "Archive",
# "Observation Room" -- generic room names that only mean something in
# context of which case they belong to).
_CASE_TITLE_KEYWORDS: Sequence[Tuple[str, Sequence[str]]] = (
    (LIGHTHOUSE, ("lighthouse",)),
    (LABORATORY, ("research facility", "laboratory")),
    (UNDERGROUND_FACILITY, ("underground", "blackwood underground")),
    (HOSPITAL, ("hospital",)),
    (ASYLUM, ("asylum",)),
    (UNDERGROUND_STATION, ("underground station",)),
    (VILLAGE, ("village", "town beneath the lake")),
    (FOREST, ("forest",)),
    (SCHOOL, ("school",)),
    (ABANDONED_BUILDING, ("hotel",)),
    (MANSION_INTERIOR, ("manor", "mansion", "necklace", "house at the end of the road")),
)

_FINAL_CASE_TITLE_MARKERS = ("final case",)


def resolve_environment(location_name: str, case_title: str = "") -> str:
    """Resolve which `EnvironmentSpec` key a location belongs to.

    Pure function of `location_name` and `case_title` -- the same
    inputs always produce the same environment id, which is what
    keeps a given location's visual identity stable across visits and
    across save/load.

    Args:
        location_name: The `Location.name` being displayed.
        case_title: The active `Case.title`, used only as a fallback
            when the location's own name is too generic to tell
            environments apart (e.g. "Main Hall", "Archive").

    Returns:
        One of the `ENVIRONMENTS` keys. Never fails to resolve --
        falls back to `GENERIC_INTERIOR` if nothing matches.
    """
    title_lower = (case_title or "").lower()
    if any(marker in title_lower for marker in _FINAL_CASE_TITLE_MARKERS):
        return FINAL_CASE

    name_lower = f" {(location_name or '').lower()} "
    for environment_id, keywords in _NAME_KEYWORDS:
        if any(keyword in name_lower for keyword in keywords):
            return environment_id

    for environment_id, keywords in _CASE_TITLE_KEYWORDS:
        if any(keyword in title_lower for keyword in keywords):
            return environment_id

    return GENERIC_INTERIOR


def spec_for(environment_id: str) -> EnvironmentSpec:
    """Return the `EnvironmentSpec` for `environment_id`, defaulting
    to `GENERIC_INTERIOR` for an unknown id rather than raising --
    a malformed/unexpected id should degrade gracefully to a plain
    room, not crash the exploration screen.
    """
    return ENVIRONMENTS.get(environment_id, ENVIRONMENTS[GENERIC_INTERIOR])


def stable_seed(location_id: str) -> int:
    """Deterministic small integer seed derived from a location id.

    Used to seed decoration placement so a given location's clutter
    layout (tree positions, window offsets, etc.) is identical every
    time it's rendered, while two different locations of the *same*
    environment kind still look laid out differently from each other.
    """
    return sum(ord(c) for c in location_id) % 9973
