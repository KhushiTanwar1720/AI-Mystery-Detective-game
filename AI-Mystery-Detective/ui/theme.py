"""
Visual theme for the AI Mystery Detective UI: color palette, font
loading, spacing constants, and horror-progression styling.

Colors/spacing are plain tuples/ints (no pygame needed to read them);
`Fonts.load()` is the only piece that actually touches pygame, and is
called once by `ui.app.App` during startup.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Tuple

Color = Tuple[int, int, int]
ColorA = Tuple[int, int, int, int]

# -- Base palette (dark detective-noir) --------------------------------------

BACKGROUND = (12, 12, 16)
BACKGROUND_PANEL = (20, 20, 26)
BACKGROUND_PANEL_LIGHT = (28, 28, 36)
BORDER = (70, 60, 50)
BORDER_LIGHT = (110, 95, 70)

TEXT_PRIMARY = (225, 220, 210)
TEXT_SECONDARY = (160, 152, 140)
TEXT_MUTED = (100, 96, 92)
TEXT_DANGER = (190, 60, 55)
TEXT_SUCCESS = (120, 170, 110)

ACCENT_GOLD = (196, 160, 80)
ACCENT_BLOOD = (140, 30, 30)
ACCENT_LANTERN = (220, 170, 90)

BUTTON_IDLE = (34, 32, 38)
BUTTON_HOVER = (52, 46, 40)
BUTTON_PRESSED = (66, 56, 40)
BUTTON_DISABLED = (24, 24, 28)
BUTTON_BORDER = ACCENT_GOLD

LOCKED = (55, 55, 60)

# Star / bar glyphs for difficulty and horror ratings.
STAR_FILLED = "\u2605"
STAR_EMPTY = "\u2606"
BAR_FILLED = "\u25A0"
BAR_EMPTY = "\u25A1"

# -- Spacing / layout ---------------------------------------------------------

PADDING_SM = 8
PADDING_MD = 16
PADDING_LG = 32
RADIUS = 6

SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 800


def horror_tier(horror_rating: int) -> int:
    """Bucket a 1-10 horror rating into one of 5 escalation tiers.

    Tiers follow the campaign design brief: 1-3, 4-6, 7-9, 10-12
    (n/a beyond 10 here so folded into tier 4), 13-15 (folded into
    tier 5) -- expressed here purely in terms of the 1-10 per-level
    `horror_rating` value:

        tier 1: rating 1-2  (subtle darkness, dim lighting)
        tier 2: rating 3-4  (fog, flicker, stronger ambience)
        tier 3: rating 5-6  (darker, hidden areas, unsettling events)
        tier 4: rating 7-8  (heavy atmosphere, dynamic lighting)
        tier 5: rating 9-10 (strongest atmosphere, final-case dread)
    """
    rating = max(1, min(10, horror_rating))
    if rating <= 2:
        return 1
    if rating <= 4:
        return 2
    if rating <= 6:
        return 3
    if rating <= 8:
        return 4
    return 5


@dataclass(frozen=True)
class HorrorPalette:
    """Background/fog/vignette styling for one horror tier."""

    background: Color
    vignette_alpha: int
    fog_alpha: int
    flicker: bool
    ambient_text: str


HORROR_PALETTES: Dict[int, HorrorPalette] = {
    1: HorrorPalette((14, 14, 18), vignette_alpha=40, fog_alpha=0, flicker=False,
                      ambient_text="The air is still."),
    2: HorrorPalette((11, 11, 15), vignette_alpha=70, fog_alpha=20, flicker=False,
                      ambient_text="Something feels slightly out of place."),
    3: HorrorPalette((9, 9, 12), vignette_alpha=100, fog_alpha=45, flicker=True,
                      ambient_text="The lights flicker, just for a moment."),
    4: HorrorPalette((6, 6, 9), vignette_alpha=140, fog_alpha=70, flicker=True,
                      ambient_text="Every shadow seems to hold its breath."),
    5: HorrorPalette((3, 3, 5), vignette_alpha=180, fog_alpha=100, flicker=True,
                      ambient_text="You are not sure you are alone."),
}


def palette_for(horror_rating: int) -> HorrorPalette:
    """Return the `HorrorPalette` for a level's 1-10 horror rating."""
    return HORROR_PALETTES[horror_tier(horror_rating)]


class Fonts:
    """Lazily-loaded shared font set.

    `Fonts.load()` must be called once, after `pygame.init()`/
    `pygame.font.init()`, before any screen uses `Fonts.title` etc.
    Kept as simple class attributes (rather than an instance passed
    everywhere) since exactly one font set is ever active at a time,
    matching how `ui.app.App` owns a single display surface.
    """

    title = None
    heading = None
    body = None
    small = None
    button = None

    @classmethod
    def load(cls) -> None:
        import pygame

        if not pygame.font.get_init():
            pygame.font.init()

        # A serif-leaning system font search keeps this dependency-free
        # of any bundled font file (see assets/fonts/ for where a real
        # custom font would be dropped in later without touching this
        # module's call sites).
        candidates = ["georgia", "timesnewroman", "garamond", "serif"]
        family = pygame.font.match_font(",".join(candidates)) or pygame.font.get_default_font()

        cls.title = pygame.font.Font(family, 48)
        cls.heading = pygame.font.Font(family, 30)
        cls.body = pygame.font.Font(family, 20)
        cls.small = pygame.font.Font(family, 16)
        cls.button = pygame.font.Font(family, 22)
