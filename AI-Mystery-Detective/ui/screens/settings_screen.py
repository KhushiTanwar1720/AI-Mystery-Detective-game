"""
Settings screen: volume, fullscreen/windowed, and resolution.

These are presentation preferences only (`ui.app.Settings`) -- never
routed through `SaveManager`/`GameState`, since they aren't gameplay
state.
"""

from __future__ import annotations

import pygame

from ui import theme
from ui.components.button import Button
from ui.screens.base import Screen

RESOLUTIONS = [(1280, 800), (1600, 900), (1920, 1080)]


class SettingsScreen(Screen):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.back_button = Button(pygame.Rect(40, theme.SCREEN_HEIGHT - 70, 160, 44), "BACK", on_click=self._back)

        self.music_down = Button(pygame.Rect(0, 0, 44, 36), "-", on_click=self._music_down)
        self.music_up = Button(pygame.Rect(0, 0, 44, 36), "+", on_click=self._music_up)
        self.sfx_down = Button(pygame.Rect(0, 0, 44, 36), "-", on_click=self._sfx_down)
        self.sfx_up = Button(pygame.Rect(0, 0, 44, 36), "+", on_click=self._sfx_up)
        self.fullscreen_toggle = Button(pygame.Rect(0, 0, 220, 44), "", on_click=self._toggle_fullscreen)
        self.resolution_button = Button(pygame.Rect(0, 0, 220, 44), "", on_click=self._cycle_resolution)

        self._layout()

    def _layout(self) -> None:
        left = 320
        self.music_down.rect = pygame.Rect(left, 200, 44, 36)
        self.music_up.rect = pygame.Rect(left + 260, 200, 44, 36)
        self.sfx_down.rect = pygame.Rect(left, 260, 44, 36)
        self.sfx_up.rect = pygame.Rect(left + 260, 260, 44, 36)
        self.fullscreen_toggle.rect = pygame.Rect(left, 320, 220, 44)
        self.resolution_button.rect = pygame.Rect(left, 380, 220, 44)
        self._refresh_labels()

    def _refresh_labels(self) -> None:
        settings = self.app.settings
        self.fullscreen_toggle.label = "FULLSCREEN" if settings.fullscreen else "WINDOWED"
        self.resolution_button.label = f"{settings.resolution[0]}x{settings.resolution[1]}"

    def _music_down(self) -> None:
        self.app.settings.music_volume = max(0.0, round(self.app.settings.music_volume - 0.1, 1))

    def _music_up(self) -> None:
        self.app.settings.music_volume = min(1.0, round(self.app.settings.music_volume + 0.1, 1))

    def _sfx_down(self) -> None:
        self.app.settings.sfx_volume = max(0.0, round(self.app.settings.sfx_volume - 0.1, 1))

    def _sfx_up(self) -> None:
        self.app.settings.sfx_volume = min(1.0, round(self.app.settings.sfx_volume + 0.1, 1))

    def _toggle_fullscreen(self) -> None:
        self.app.settings.fullscreen = not self.app.settings.fullscreen
        self.app.apply_display_settings()
        self._refresh_labels()

    def _cycle_resolution(self) -> None:
        current = self.app.settings.resolution
        index = RESOLUTIONS.index(current) if current in RESOLUTIONS else -1
        next_res = RESOLUTIONS[(index + 1) % len(RESOLUTIONS)]
        self.app.settings.resolution = next_res
        self.app.apply_display_settings()
        self._refresh_labels()

    def _back(self) -> None:
        self.manager.pop()

    def handle_event(self, event: "pygame.event.Event") -> None:
        for button in (
            self.music_down, self.music_up, self.sfx_down, self.sfx_up,
            self.fullscreen_toggle, self.resolution_button, self.back_button,
        ):
            button.handle_event(event)

    def update(self, dt: float) -> None:
        for button in (
            self.music_down, self.music_up, self.sfx_down, self.sfx_up,
            self.fullscreen_toggle, self.resolution_button, self.back_button,
        ):
            button.update(dt)

    def draw(self, surface: "pygame.Surface") -> None:
        surface.fill(theme.BACKGROUND)
        surface.blit(theme.Fonts.heading.render("SETTINGS", True, theme.ACCENT_GOLD), (40, 40))

        settings = self.app.settings
        surface.blit(theme.Fonts.body.render("Music volume", True, theme.TEXT_PRIMARY), (320, 160))
        surface.blit(theme.Fonts.small.render(f"{int(settings.music_volume * 100)}%", True, theme.TEXT_SECONDARY), (430, 208))

        surface.blit(theme.Fonts.body.render("Sound effects", True, theme.TEXT_PRIMARY), (320, 232))
        surface.blit(theme.Fonts.small.render(f"{int(settings.sfx_volume * 100)}%", True, theme.TEXT_SECONDARY), (430, 268))

        for button in (
            self.music_down, self.music_up, self.sfx_down, self.sfx_up,
            self.fullscreen_toggle, self.resolution_button, self.back_button,
        ):
            button.draw(surface)
