"""
Procedural environment renderer.

Draws a full-screen backdrop for a `ui.environments.EnvironmentSpec`
using only pygame primitives (gradients, rects, silhouettes, an alpha
fog overlay) -- no external image files are required, so the game
never depends on downloading or bundling assets to look
environment-appropriate (asset files, if later added, are additive
and optional -- see `ui/theme.py`'s `assets/` layout).

`render_environment()` is the single entry point every screen should
call; it dispatches on `EnvironmentSpec.renderer` to one of the four
private `_render_*` layout strategies, then layers a horror-tier fog/
vignette on top so environment identity (what kind of place this is)
and horror intensity (how dark/foggy/oppressive it feels) stay two
independent, composable dials.
"""

from __future__ import annotations

import math
import random
from collections import OrderedDict

import pygame

from ui import theme
from ui.environments import (
    RENDER_FINAL,
    RENDER_INTERIOR,
    RENDER_OUTDOOR,
    RENDER_UNDERGROUND,
    EnvironmentSpec,
)

# Bounded cache of fully-rendered (gradient + decorations + fog +
# vignette) backdrops, keyed by everything that affects their pixels.
# Redrawing a location's backdrop is dozens of primitive draw calls;
# caching means a location visited repeatedly (very common -- players
# routinely re-enter the same room) costs one cheap blit instead.
# Bounded (not a plain dict) so a long play session across many
# locations/levels can't grow this without limit.
_BASE_CACHE: "OrderedDict[tuple, pygame.Surface]" = OrderedDict()
_BASE_CACHE_MAXSIZE = 24


def _cached_base(spec: EnvironmentSpec, seed: int, horror_fog_alpha: int, size) -> "pygame.Surface":
    key = (id(spec), seed, horror_fog_alpha, size)
    cached = _BASE_CACHE.get(key)
    if cached is not None:
        _BASE_CACHE.move_to_end(key)
        return cached

    width, height = size
    base = pygame.Surface(size)
    rng = random.Random(seed)

    if spec.renderer == RENDER_OUTDOOR:
        _render_outdoor(base, spec, rng, width, height)
    elif spec.renderer == RENDER_UNDERGROUND:
        _render_underground(base, spec, rng, width, height)
    elif spec.renderer == RENDER_FINAL:
        _render_final(base, spec, rng, width, height)
    else:
        _render_interior(base, spec, rng, width, height)

    if horror_fog_alpha > 0:
        _apply_fog(base, horror_fog_alpha, spec.accent_color)
    _apply_vignette(base, width, height)

    _BASE_CACHE[key] = base
    if len(_BASE_CACHE) > _BASE_CACHE_MAXSIZE:
        _BASE_CACHE.popitem(last=False)
    return base


def render_environment(
    surface: "pygame.Surface",
    spec: EnvironmentSpec,
    seed: int,
    horror_fog_alpha: int,
    flicker: bool = False,
) -> None:
    """Draw `spec`'s full-screen backdrop onto `surface`.

    Args:
        surface: Destination surface (drawn full-size, from (0, 0)).
        spec: The environment's visual spec (see `ui.environments`).
        seed: Stable per-location seed (see
            `ui.environments.stable_seed`) so decoration placement is
            identical on every visit to the same location, while
            differing between different locations.
        horror_fog_alpha: 0-255 fog overlay strength contributed by
            the level's horror tier (see `ui.theme.palette_for`).
            Combined additively with `spec.fog_boost`.
        flicker: Whether the active horror tier calls for a flickering
            light effect (see `ui.theme.HorrorPalette.flicker`). Drawn
            fresh every call (never cached) so it reads as a live
            effect rather than a fixed part of the location's look.
    """
    total_fog = min(255, horror_fog_alpha + int(spec.fog_boost * 255))
    base = _cached_base(spec, seed, total_fog, surface.get_size())
    surface.blit(base, (0, 0))

    if flicker and random.random() < 0.5:
        _apply_flicker(surface, random)


# -- Shared primitives ---------------------------------------------------


def _vertical_gradient(surface, top_color, bottom_color, rect):
    x, y, w, h = rect
    if h <= 0:
        return
    for row in range(h):
        t = row / max(1, h - 1)
        color = tuple(int(top_color[i] + (bottom_color[i] - top_color[i]) * t) for i in range(3))
        pygame.draw.line(surface, color, (x, y + row), (x + w, y + row))


def _apply_fog(surface, alpha: int, tint):
    width, height = surface.get_size()
    fog = pygame.Surface((width, height), pygame.SRCALPHA)
    muted = tuple(int(c * 0.25) for c in tint)
    fog.fill((*muted, alpha))
    surface.blit(fog, (0, 0))


def _apply_vignette(surface, width, height):
    # A translucent shrinking-border frame reads as a vignette
    # (darkened edges, clear center). Drawn in a fixed number of
    # coarse bands rather than one rect per pixel of thickness, to
    # keep this affordable every frame.
    border = pygame.Surface((width, height), pygame.SRCALPHA)
    thickness = int(min(width, height) * 0.18)
    bands = 18
    step = max(1, thickness // bands)
    for i in range(0, thickness, step):
        alpha = int(55 * (1 - i / thickness))
        pygame.draw.rect(border, (0, 0, 0, alpha), pygame.Rect(i, i, width - 2 * i, height - 2 * i), width=step)
    surface.blit(border, (0, 0))


def _apply_flicker(surface, rng):
    width, height = surface.get_size()
    flash = pygame.Surface((width, height), pygame.SRCALPHA)
    alpha = rng.randint(10, 35)
    flash.fill((255, 250, 230, alpha))
    surface.blit(flash, (0, 0))


# -- Interior ------------------------------------------------------------


def _render_interior(surface, spec: EnvironmentSpec, rng, width, height):
    floor_y = int(height * 0.68)
    _vertical_gradient(surface, spec.top_color, spec.bottom_color, (0, 0, width, floor_y))
    pygame.draw.rect(surface, spec.floor_color, pygame.Rect(0, floor_y, width, height - floor_y))
    pygame.draw.line(surface, tuple(min(255, c + 15) for c in spec.floor_color), (0, floor_y), (width, floor_y), 2)

    for name in spec.decorations:
        drawer = DECORATION_DRAWERS.get(name)
        if drawer is not None:
            drawer(surface, spec, rng, width, height, floor_y)


# -- Outdoor ---------------------------------------------------------------


def _render_outdoor(surface, spec: EnvironmentSpec, rng, width, height):
    horizon_y = int(height * 0.62)
    _vertical_gradient(surface, spec.top_color, spec.bottom_color, (0, 0, width, horizon_y))
    pygame.draw.rect(surface, spec.floor_color, pygame.Rect(0, horizon_y, width, height - horizon_y))
    pygame.draw.line(surface, tuple(min(255, c + 10) for c in spec.floor_color), (0, horizon_y), (width, horizon_y), 2)

    # A soft moon/light source anchors every outdoor scene.
    moon_x = int(width * 0.82)
    moon_y = int(height * 0.18)
    pygame.draw.circle(surface, tuple(min(255, c + 60) for c in spec.accent_color), (moon_x, moon_y), 28)
    pygame.draw.circle(surface, spec.bottom_color, (moon_x, moon_y), 28, width=0)
    pygame.draw.circle(surface, tuple(min(255, c + 80) for c in spec.accent_color), (moon_x - 6, moon_y - 4), 24)

    for name in spec.decorations:
        drawer = DECORATION_DRAWERS.get(name)
        if drawer is not None:
            drawer(surface, spec, rng, width, height, horizon_y)


# -- Underground -----------------------------------------------------------


def _render_underground(surface, spec: EnvironmentSpec, rng, width, height):
    # Converging tunnel walls toward a vanishing point, giving a
    # distinct sense of enclosure vs. the flat interior/outdoor layouts.
    vanish = (width // 2, int(height * 0.42))
    surface.fill(spec.bottom_color)
    pygame.draw.polygon(
        surface, spec.top_color,
        [(0, 0), (width, 0), vanish[0] + 140, vanish[1] - 40, (vanish[0] - 140, vanish[1] - 40)],
    )
    floor_y = int(height * 0.72)
    pygame.draw.polygon(
        surface, spec.floor_color,
        [(0, height), (width, height), (vanish[0] + 120, floor_y), (vanish[0] - 120, floor_y)],
    )

    for name in spec.decorations:
        drawer = DECORATION_DRAWERS.get(name)
        if drawer is not None:
            drawer(surface, spec, rng, width, height, floor_y)


# -- Final case (bespoke) ---------------------------------------------------


def _render_final(surface, spec: EnvironmentSpec, rng, width, height):
    surface.fill(spec.bottom_color)
    center = (width // 2, int(height * 0.55))
    max_radius = int(math.hypot(width, height) / 2)
    for i in range(10, 0, -1):
        radius = int(max_radius * (i / 10))
        t = i / 10
        color = tuple(int(spec.bottom_color[c] + (spec.top_color[c] - spec.bottom_color[c]) * (1 - t)) for c in range(3))
        pygame.draw.circle(surface, color, center, radius)

    floor_y = int(height * 0.72)
    pygame.draw.rect(surface, spec.floor_color, pygame.Rect(0, floor_y, width, height - floor_y))

    for name in spec.decorations:
        drawer = DECORATION_DRAWERS.get(name)
        if drawer is not None:
            drawer(surface, spec, rng, width, height, floor_y)


# -- Decoration silhouettes --------------------------------------------------
#
# Each drawer takes (surface, spec, rng, width, height, ground_y) and
# draws a handful of simple silhouette shapes. `rng` is seeded per
# location (see `render_environment`), so placement is stable per
# location but varies location-to-location.


def _dark(color, factor=0.4):
    return tuple(int(c * factor) for c in color)


def _draw_window_arched(surface, spec, rng, width, height, ground_y):
    for i in range(2):
        x = int(width * (0.15 + i * 0.6))
        w, h = 90, 160
        y = int(ground_y * 0.15)
        pygame.draw.rect(surface, spec.accent_color, pygame.Rect(x, y, w, h), border_radius=30)
        pygame.draw.rect(surface, _dark(spec.top_color, 0.6), pygame.Rect(x + 6, y + 6, w - 12, h - 12), border_radius=26)


def _draw_window_small(surface, spec, rng, width, height, ground_y):
    x = int(width * 0.75)
    y = int(ground_y * 0.2)
    pygame.draw.rect(surface, spec.accent_color, pygame.Rect(x, y, 70, 90))
    pygame.draw.line(surface, _dark(spec.accent_color), (x + 35, y), (x + 35, y + 90), 2)


def _draw_window_barred(surface, spec, rng, width, height, ground_y):
    x = int(width * 0.72)
    y = int(ground_y * 0.15)
    pygame.draw.rect(surface, spec.accent_color, pygame.Rect(x, y, 80, 120))
    for i in range(1, 5):
        bar_x = x + i * 16
        pygame.draw.line(surface, spec.floor_color, (bar_x, y), (bar_x, y + 120), 3)


def _draw_window_round(surface, spec, rng, width, height, ground_y):
    cx, cy = int(width * 0.78), int(ground_y * 0.25)
    pygame.draw.circle(surface, spec.accent_color, (cx, cy), 50)
    pygame.draw.circle(surface, _dark(spec.top_color, 0.5), (cx, cy), 42)


def _draw_chandelier(surface, spec, rng, width, height, ground_y):
    cx = width // 2
    pygame.draw.line(surface, spec.accent_color, (cx, 0), (cx, 60), 2)
    pygame.draw.circle(surface, spec.accent_color, (cx, 70), 22)
    for dx in (-30, 0, 30):
        pygame.draw.circle(surface, spec.accent_color, (cx + dx, 90), 6)


def _draw_chandelier_large(surface, spec, rng, width, height, ground_y):
    cx = width // 2
    pygame.draw.line(surface, spec.accent_color, (cx, 0), (cx, 90), 3)
    pygame.draw.circle(surface, spec.accent_color, (cx, 100), 34)
    for angle in range(0, 360, 45):
        dx = int(50 * math.cos(math.radians(angle)))
        dy = int(20 * math.sin(math.radians(angle)))
        pygame.draw.circle(surface, spec.accent_color, (cx + dx, 100 + dy), 5)


def _draw_pillar(surface, spec, rng, width, height, ground_y):
    for i in range(3):
        x = int(width * (0.1 + i * 0.35))
        pygame.draw.rect(surface, _dark(spec.top_color, 0.7), pygame.Rect(x, 30, 30, ground_y - 30))
        pygame.draw.rect(surface, _dark(spec.top_color, 0.9), pygame.Rect(x, 30, 30, 12))


def _draw_portrait_frame(surface, spec, rng, width, height, ground_y):
    x = int(width * 0.55)
    y = int(ground_y * 0.2)
    pygame.draw.rect(surface, spec.accent_color, pygame.Rect(x, y, 100, 130), width=4)
    pygame.draw.rect(surface, _dark(spec.top_color, 0.5), pygame.Rect(x + 6, y + 6, 88, 118))


def _draw_drape(surface, spec, rng, width, height, ground_y):
    x = int(width * 0.08)
    pygame.draw.polygon(surface, _dark(spec.accent_color, 0.6), [(x, 0), (x + 60, 0), (x + 40, ground_y), (x, ground_y)])


def _draw_fireplace(surface, spec, rng, width, height, ground_y):
    x = int(width * 0.5) - 60
    y = ground_y - 140
    pygame.draw.rect(surface, _dark(spec.top_color, 0.6), pygame.Rect(x, y, 120, 140))
    pygame.draw.rect(surface, (60, 30, 10), pygame.Rect(x + 20, y + 60, 80, 80))
    pygame.draw.polygon(surface, spec.accent_color, [(x + 40, y + 130), (x + 60, y + 90), (x + 80, y + 130)])


def _draw_armchair(surface, spec, rng, width, height, ground_y):
    x = int(width * 0.2)
    y = ground_y - 70
    pygame.draw.rect(surface, _dark(spec.accent_color, 0.6), pygame.Rect(x, y, 90, 70), border_radius=10)
    pygame.draw.rect(surface, _dark(spec.accent_color, 0.6), pygame.Rect(x - 10, y - 40, 20, 110), border_radius=6)


def _draw_counter(surface, spec, rng, width, height, ground_y):
    pygame.draw.rect(surface, _dark(spec.accent_color, 0.5), pygame.Rect(0, ground_y - 60, width, 60))
    pygame.draw.line(surface, spec.accent_color, (0, ground_y - 60), (width, ground_y - 60), 3)


def _draw_cabinet(surface, spec, rng, width, height, ground_y):
    x = int(width * 0.7)
    pygame.draw.rect(surface, _dark(spec.top_color, 0.7), pygame.Rect(x, ground_y - 160, 120, 100))
    for i in range(3):
        pygame.draw.line(surface, spec.accent_color, (x, ground_y - 160 + i * 33), (x + 120, ground_y - 160 + i * 33), 1)


def _draw_hanging_pot(surface, spec, rng, width, height, ground_y):
    for i in range(3):
        x = int(width * (0.3 + i * 0.15))
        pygame.draw.line(surface, spec.accent_color, (x, 0), (x, 40), 2)
        pygame.draw.circle(surface, _dark(spec.accent_color, 0.7), (x, 50), 12)


def _draw_hedge(surface, spec, rng, width, height, ground_y):
    for i in range(6):
        x = int(width * i / 6)
        h = 30 + rng.randint(0, 20)
        pygame.draw.ellipse(surface, _dark(spec.accent_color, 0.7), pygame.Rect(x, ground_y - h, width // 5, h))


def _draw_fountain(surface, spec, rng, width, height, ground_y):
    cx = width // 2
    pygame.draw.ellipse(surface, _dark(spec.accent_color, 0.5), pygame.Rect(cx - 60, ground_y - 30, 120, 40))
    pygame.draw.rect(surface, _dark(spec.accent_color, 0.6), pygame.Rect(cx - 8, ground_y - 90, 16, 60))
    pygame.draw.circle(surface, spec.accent_color, (cx, ground_y - 95), 10)


def _draw_tree_small(surface, spec, rng, width, height, ground_y):
    x = rng.randint(int(width * 0.1), int(width * 0.9))
    trunk_h = 40
    pygame.draw.rect(surface, _dark((90, 60, 40)), pygame.Rect(x - 4, ground_y - trunk_h, 8, trunk_h))
    pygame.draw.circle(surface, _dark(spec.accent_color, 0.8), (x, ground_y - trunk_h - 10), 26)


def _draw_tree_tall(surface, spec, rng, width, height, ground_y):
    x = rng.randint(int(width * 0.05), int(width * 0.95))
    trunk_h = 90 + rng.randint(0, 60)
    pygame.draw.rect(surface, _dark((60, 45, 35)), pygame.Rect(x - 6, ground_y - trunk_h, 12, trunk_h))
    pygame.draw.polygon(
        surface, _dark(spec.accent_color, 0.6),
        [(x, ground_y - trunk_h - 120), (x - 44, ground_y - trunk_h), (x + 44, ground_y - trunk_h)],
    )


def _draw_fence(surface, spec, rng, width, height, ground_y):
    for x in range(0, width, 40):
        pygame.draw.rect(surface, _dark(spec.floor_color, 1.4), pygame.Rect(x, ground_y - 30, 6, 30))


def _draw_fence_broken(surface, spec, rng, width, height, ground_y):
    for x in range(0, width, 50):
        tilt = rng.randint(-8, 8)
        pygame.draw.line(surface, _dark(spec.accent_color, 0.6), (x, ground_y), (x + tilt, ground_y - 26), 4)


def _draw_cabin_silhouette(surface, spec, rng, width, height, ground_y):
    x = int(width * 0.72)
    w, h = 120, 90
    pygame.draw.rect(surface, _dark(spec.accent_color, 0.4), pygame.Rect(x, ground_y - h, w, h))
    pygame.draw.polygon(surface, _dark(spec.accent_color, 0.5), [(x - 10, ground_y - h), (x + w // 2, ground_y - h - 40), (x + w + 10, ground_y - h)])
    pygame.draw.rect(surface, spec.accent_color, pygame.Rect(x + w // 2 - 10, ground_y - 30, 20, 30))


def _draw_house_silhouette(surface, spec, rng, width, height, ground_y):
    for i in range(3):
        x = int(width * (0.1 + i * 0.3))
        w, h = 80, 60 + rng.randint(0, 20)
        pygame.draw.rect(surface, _dark(spec.accent_color, 0.35), pygame.Rect(x, ground_y - h, w, h))
        pygame.draw.polygon(surface, _dark(spec.accent_color, 0.45), [(x - 8, ground_y - h), (x + w // 2, ground_y - h - 30), (x + w + 8, ground_y - h)])


def _draw_church_spire(surface, spec, rng, width, height, ground_y):
    x = int(width * 0.55)
    w, h = 60, 100
    pygame.draw.rect(surface, _dark(spec.accent_color, 0.4), pygame.Rect(x, ground_y - h, w, h))
    pygame.draw.polygon(surface, _dark(spec.accent_color, 0.5), [(x - 6, ground_y - h), (x + w // 2, ground_y - h - 60), (x + w + 6, ground_y - h)])
    pygame.draw.line(surface, spec.accent_color, (x + w // 2, ground_y - h - 60), (x + w // 2, ground_y - h - 80), 3)


def _draw_well_stone(surface, spec, rng, width, height, ground_y):
    cx = int(width * 0.3)
    pygame.draw.ellipse(surface, _dark(spec.accent_color, 0.5), pygame.Rect(cx - 40, ground_y - 30, 80, 30))
    pygame.draw.rect(surface, _dark(spec.accent_color, 0.6), pygame.Rect(cx - 40, ground_y - 60, 8, 40))
    pygame.draw.rect(surface, _dark(spec.accent_color, 0.6), pygame.Rect(cx + 32, ground_y - 60, 8, 40))


def _draw_lockers(surface, spec, rng, width, height, ground_y):
    x = 40
    for i in range(6):
        pygame.draw.rect(surface, spec.accent_color, pygame.Rect(x, ground_y - 140, 40, 140), width=2)
        x += 46


def _draw_chalkboard(surface, spec, rng, width, height, ground_y):
    x = int(width * 0.55)
    pygame.draw.rect(surface, (20, 40, 30), pygame.Rect(x, 80, 220, 120))
    pygame.draw.rect(surface, _dark(spec.accent_color, 0.7), pygame.Rect(x, 80, 220, 120), width=4)


def _draw_desk_row(surface, spec, rng, width, height, ground_y):
    for i in range(3):
        x = int(width * (0.15 + i * 0.2))
        pygame.draw.rect(surface, _dark(spec.accent_color, 0.5), pygame.Rect(x, ground_y - 40, 60, 20))


def _draw_hospital_bed(surface, spec, rng, width, height, ground_y):
    x = int(width * 0.35)
    pygame.draw.rect(surface, _dark(spec.accent_color, 0.4), pygame.Rect(x, ground_y - 40, 160, 20))
    pygame.draw.rect(surface, spec.accent_color, pygame.Rect(x, ground_y - 60, 20, 20))


def _draw_curtain_divider(surface, spec, rng, width, height, ground_y):
    x = int(width * 0.65)
    for i in range(8):
        pygame.draw.line(surface, _dark(spec.accent_color, 0.4), (x + i * 8, 20), (x + i * 8, ground_y - 20), 2)


def _draw_monitor_stand(surface, spec, rng, width, height, ground_y):
    x = int(width * 0.15)
    pygame.draw.rect(surface, (10, 10, 10), pygame.Rect(x, ground_y - 100, 40, 30))
    pygame.draw.circle(surface, spec.accent_color, (x + 20, ground_y - 85), 4)


def _draw_flicker_light(surface, spec, rng, width, height, ground_y):
    x = width // 2
    pygame.draw.line(surface, spec.accent_color, (x, 0), (x, 30), 2)
    if rng.random() < 0.7:
        pygame.draw.circle(surface, spec.accent_color, (x, 36), 10)


def _draw_restraint_chair(surface, spec, rng, width, height, ground_y):
    x = int(width * 0.45)
    pygame.draw.rect(surface, _dark(spec.accent_color, 0.5), pygame.Rect(x, ground_y - 90, 50, 90))
    pygame.draw.line(surface, spec.accent_color, (x, ground_y - 60), (x + 50, ground_y - 60), 2)


def _draw_door_heavy(surface, spec, rng, width, height, ground_y):
    x = int(width * 0.75)
    pygame.draw.rect(surface, _dark(spec.accent_color, 0.4), pygame.Rect(x, ground_y - 180, 90, 180), width=6)
    pygame.draw.circle(surface, spec.accent_color, (x + 70, ground_y - 90), 5)


def _draw_stain(surface, spec, rng, width, height, ground_y):
    x = rng.randint(int(width * 0.2), int(width * 0.8))
    pygame.draw.ellipse(surface, _dark(spec.accent_color, 0.3), pygame.Rect(x, ground_y - 60, 30, 50))


def _draw_platform_edge(surface, spec, rng, width, height, ground_y):
    pygame.draw.rect(surface, spec.accent_color, pygame.Rect(0, ground_y - 10, width, 6))


def _draw_pillar_tiled(surface, spec, rng, width, height, ground_y):
    for i in range(4):
        x = int(width * (0.1 + i * 0.28))
        pygame.draw.rect(surface, _dark(spec.top_color, 0.6), pygame.Rect(x, 20, 26, ground_y - 20))


def _draw_sign_faded(surface, spec, rng, width, height, ground_y):
    x = int(width * 0.5) - 60
    pygame.draw.rect(surface, _dark(spec.accent_color, 0.5), pygame.Rect(x, 50, 120, 30), width=2)


def _draw_tracks(surface, spec, rng, width, height, ground_y):
    pygame.draw.line(surface, _dark(spec.accent_color, 0.6), (0, height - 10), (width, height - 10), 4)
    pygame.draw.line(surface, _dark(spec.accent_color, 0.6), (0, height - 24), (width, height - 24), 4)


def _draw_spiral_stairs(surface, spec, rng, width, height, ground_y):
    cx = width // 2
    for i in range(8):
        y = ground_y - i * 30
        w = 140 - i * 6
        pygame.draw.ellipse(surface, spec.accent_color, pygame.Rect(cx - w // 2, y, w, 14), width=2)


def _draw_lantern_glow(surface, spec, rng, width, height, ground_y):
    cx = width // 2
    pygame.draw.circle(surface, spec.accent_color, (cx, 60), 30)
    pygame.draw.circle(surface, tuple(min(255, c + 60) for c in spec.accent_color), (cx, 60), 16)


def _draw_storm_streaks(surface, spec, rng, width, height, ground_y):
    for _ in range(10):
        x = rng.randint(0, width)
        y = rng.randint(0, ground_y)
        pygame.draw.line(surface, (180, 190, 210), (x, y), (x - 10, y + 30), 1)


def _draw_server_rack(surface, spec, rng, width, height, ground_y):
    for i in range(4):
        x = int(width * (0.1 + i * 0.2))
        pygame.draw.rect(surface, _dark(spec.top_color, 0.6), pygame.Rect(x, ground_y - 140, 50, 140))
        for j in range(5):
            color = spec.accent_color if rng.random() < 0.5 else _dark(spec.accent_color, 0.5)
            pygame.draw.circle(surface, color, (x + 40, ground_y - 130 + j * 25), 3)


def _draw_monitor_bank(surface, spec, rng, width, height, ground_y):
    x = int(width * 0.6)
    for i in range(3):
        pygame.draw.rect(surface, spec.accent_color, pygame.Rect(x + i * 50, 60, 40, 30), width=2)


def _draw_pipes_metal(surface, spec, rng, width, height, ground_y):
    for i in range(3):
        y = 30 + i * 20
        pygame.draw.line(surface, _dark(spec.accent_color, 0.6), (0, y), (width, y), 5)


def _draw_pipes_thin(surface, spec, rng, width, height, ground_y):
    pygame.draw.line(surface, _dark(spec.accent_color, 0.5), (0, 20), (width, 20), 3)
    pygame.draw.line(surface, _dark(spec.accent_color, 0.5), (0, 34), (width, 34), 3)


def _draw_pipes_thick(surface, spec, rng, width, height, ground_y):
    for i in range(2):
        y = 30 + i * 40
        pygame.draw.line(surface, _dark(spec.accent_color, 0.6), (0, y), (width, y), 10)


def _draw_support_beam(surface, spec, rng, width, height, ground_y):
    for i in range(3):
        x = int(width * (0.2 + i * 0.3))
        pygame.draw.rect(surface, _dark(spec.top_color, 0.5), pygame.Rect(x, 10, 14, ground_y - 10))


def _draw_warning_light(surface, spec, rng, width, height, ground_y):
    x = int(width * 0.85)
    color = spec.accent_color if rng.random() < 0.6 else _dark(spec.accent_color, 0.4)
    pygame.draw.circle(surface, color, (x, 40), 10)


def _draw_warning_tape(surface, spec, rng, width, height, ground_y):
    y = ground_y - 100
    for x in range(0, width, 30):
        color = (200, 170, 40) if (x // 30) % 2 == 0 else (20, 20, 20)
        pygame.draw.line(surface, color, (x, y), (x + 20, y), 6)


def _draw_bed_frame(surface, spec, rng, width, height, ground_y):
    x = int(width * 0.3)
    pygame.draw.rect(surface, _dark(spec.accent_color, 0.5), pygame.Rect(x, ground_y - 50, 140, 20))
    pygame.draw.rect(surface, _dark(spec.accent_color, 0.6), pygame.Rect(x, ground_y - 80, 12, 30))


def _draw_dresser(surface, spec, rng, width, height, ground_y):
    x = int(width * 0.68)
    pygame.draw.rect(surface, _dark(spec.accent_color, 0.5), pygame.Rect(x, ground_y - 60, 80, 60))


def _draw_cobweb(surface, spec, rng, width, height, ground_y):
    x, y = int(width * 0.1), 10
    for i in range(4):
        pygame.draw.line(surface, spec.accent_color, (x, y), (x + 20 + i * 5, y + 20 + i * 5), 1)


def _draw_peeling_wallpaper(surface, spec, rng, width, height, ground_y):
    for _ in range(5):
        x = rng.randint(0, width - 40)
        y = rng.randint(0, ground_y - 60)
        pygame.draw.polygon(surface, _dark(spec.top_color, 0.5), [(x, y), (x + 20, y + 10), (x + 10, y + 40)])


def _draw_reception_desk(surface, spec, rng, width, height, ground_y):
    pygame.draw.rect(surface, _dark(spec.accent_color, 0.5), pygame.Rect(width // 2 - 100, ground_y - 60, 200, 60))


def _draw_broken_light(surface, spec, rng, width, height, ground_y):
    x = int(width * 0.5)
    pygame.draw.line(surface, spec.accent_color, (x, 0), (x - 20, 40), 2)


def _draw_door_row(surface, spec, rng, width, height, ground_y):
    for i in range(4):
        x = int(width * (0.05 + i * 0.24))
        pygame.draw.rect(surface, _dark(spec.accent_color, 0.5), pygame.Rect(x, ground_y - 130, 50, 130), width=3)


def _draw_desk(surface, spec, rng, width, height, ground_y):
    x = int(width * 0.35)
    pygame.draw.rect(surface, _dark(spec.accent_color, 0.5), pygame.Rect(x, ground_y - 45, 140, 20))


def _draw_filing_cabinet(surface, spec, rng, width, height, ground_y):
    x = int(width * 0.72)
    pygame.draw.rect(surface, _dark(spec.top_color, 0.6), pygame.Rect(x, ground_y - 110, 60, 110))
    for i in range(3):
        pygame.draw.line(surface, spec.accent_color, (x, ground_y - 110 + i * 36), (x + 60, ground_y - 110 + i * 36), 1)


def _draw_lamp(surface, spec, rng, width, height, ground_y):
    x = int(width * 0.15)
    pygame.draw.line(surface, spec.accent_color, (x, ground_y - 90), (x, ground_y - 40), 3)
    pygame.draw.circle(surface, spec.accent_color, (x, ground_y - 100), 14)


def _draw_bare_bulb(surface, spec, rng, width, height, ground_y):
    x = width // 2
    pygame.draw.line(surface, spec.accent_color, (x, 0), (x, 30), 2)
    pygame.draw.circle(surface, spec.accent_color, (x, 36), 8)


def _draw_crate(surface, spec, rng, width, height, ground_y):
    for i in range(3):
        x = int(width * (0.15 + i * 0.12))
        size = 30 + rng.randint(0, 10)
        pygame.draw.rect(surface, _dark(spec.accent_color, 0.4), pygame.Rect(x, ground_y - size, size, size))


def _draw_chamber_pillars(surface, spec, rng, width, height, ground_y):
    for i in range(5):
        x = int(width * (0.05 + i * 0.22))
        pygame.draw.rect(surface, _dark(spec.top_color, 0.5), pygame.Rect(x, 10, 20, ground_y - 10))


def _draw_candle_ring(surface, spec, rng, width, height, ground_y):
    cx, cy = width // 2, ground_y - 30
    for angle in range(0, 360, 30):
        x = cx + int(120 * math.cos(math.radians(angle)))
        y = cy + int(30 * math.sin(math.radians(angle)))
        pygame.draw.circle(surface, spec.accent_color, (x, y), 3)


def _draw_shattered_glass(surface, spec, rng, width, height, ground_y):
    for _ in range(12):
        x = rng.randint(0, width)
        y = rng.randint(ground_y - 20, ground_y)
        pygame.draw.line(surface, spec.accent_color, (x, y), (x + rng.randint(-6, 6), y - rng.randint(2, 8)), 1)


def _draw_eye_glow(surface, spec, rng, width, height, ground_y):
    cx, cy = width // 2, int(height * 0.3)
    pygame.draw.circle(surface, spec.accent_color, (cx, cy), 6)
    pygame.draw.circle(surface, tuple(min(255, c + 80) for c in spec.accent_color), (cx, cy), 3)


DECORATION_DRAWERS = {
    "window_arched": _draw_window_arched,
    "window_small": _draw_window_small,
    "window_barred": _draw_window_barred,
    "window_round": _draw_window_round,
    "chandelier": _draw_chandelier,
    "chandelier_large": _draw_chandelier_large,
    "pillar": _draw_pillar,
    "portrait_frame": _draw_portrait_frame,
    "drape": _draw_drape,
    "fireplace": _draw_fireplace,
    "armchair": _draw_armchair,
    "counter": _draw_counter,
    "cabinet": _draw_cabinet,
    "hanging_pot": _draw_hanging_pot,
    "hedge": _draw_hedge,
    "fountain": _draw_fountain,
    "tree_small": _draw_tree_small,
    "tree_tall": _draw_tree_tall,
    "fence": _draw_fence,
    "fence_broken": _draw_fence_broken,
    "cabin_silhouette": _draw_cabin_silhouette,
    "house_silhouette": _draw_house_silhouette,
    "church_spire": _draw_church_spire,
    "well_stone": _draw_well_stone,
    "lockers": _draw_lockers,
    "chalkboard": _draw_chalkboard,
    "desk_row": _draw_desk_row,
    "hospital_bed": _draw_hospital_bed,
    "curtain_divider": _draw_curtain_divider,
    "monitor_stand": _draw_monitor_stand,
    "flicker_light": _draw_flicker_light,
    "restraint_chair": _draw_restraint_chair,
    "door_heavy": _draw_door_heavy,
    "stain": _draw_stain,
    "platform_edge": _draw_platform_edge,
    "pillar_tiled": _draw_pillar_tiled,
    "sign_faded": _draw_sign_faded,
    "tracks": _draw_tracks,
    "spiral_stairs": _draw_spiral_stairs,
    "lantern_glow": _draw_lantern_glow,
    "storm_streaks": _draw_storm_streaks,
    "server_rack": _draw_server_rack,
    "monitor_bank": _draw_monitor_bank,
    "pipes_metal": _draw_pipes_metal,
    "pipes_thin": _draw_pipes_thin,
    "pipes_thick": _draw_pipes_thick,
    "support_beam": _draw_support_beam,
    "warning_light": _draw_warning_light,
    "warning_tape": _draw_warning_tape,
    "bed_frame": _draw_bed_frame,
    "dresser": _draw_dresser,
    "cobweb": _draw_cobweb,
    "peeling_wallpaper": _draw_peeling_wallpaper,
    "reception_desk": _draw_reception_desk,
    "broken_light": _draw_broken_light,
    "door_row": _draw_door_row,
    "desk": _draw_desk,
    "filing_cabinet": _draw_filing_cabinet,
    "lamp": _draw_lamp,
    "bare_bulb": _draw_bare_bulb,
    "crate": _draw_crate,
    "chamber_pillars": _draw_chamber_pillars,
    "candle_ring": _draw_candle_ring,
    "shattered_glass": _draw_shattered_glass,
    "eye_glow": _draw_eye_glow,
}
