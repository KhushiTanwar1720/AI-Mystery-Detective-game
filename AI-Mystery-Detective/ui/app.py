"""
PygameApp: the top-level graphical application object.

Owns the pygame display/clock, one live `GameController` (the single
bridge into every backend system -- investigation, evidence, clues,
suspects, interrogation, AI analysis, scoring, achievements, save/
load, locations), the `ScreenManager`, and a small `Settings` object
for audio/display preferences (UI-only state; never backend state).

Usage:
    from ui.app import PygameApp
    PygameApp().run()
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

import pygame

from game.game_controller import GameController
from ui import theme
from ui.state_manager import ScreenManager

FPS = 60


@dataclass
class Settings:
    """UI-only settings (never persisted through SaveManager/GameState --
    these are presentation preferences, not gameplay state).
    """

    music_volume: float = 0.6
    sfx_volume: float = 0.8
    fullscreen: bool = False
    resolution: tuple = (theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT)


class PygameApp:
    """Owns the pygame window/loop and wires the UI to the backend."""

    def __init__(self, player_id: str = "detective_1", player_name: str = "Detective") -> None:
        pygame.init()
        theme.Fonts.load()

        self.settings = Settings()
        self._create_display()

        pygame.display.set_caption("AI Mystery Detective")

        self.clock = pygame.time.Clock()
        self.running = True

        # The single backend bridge every screen uses -- created once,
        # for the lifetime of the app, exactly like `game.app.App`
        # does for the CLI. Screens never construct their own
        # GameController.
        self.controller = GameController(player_id=player_id, player_name=player_name)

        self.manager = ScreenManager(self.screen)

        # Imported here (not at module load time) so importing
        # ui.app doesn't require the screens package to already be
        # fully wired -- avoids a circular import between
        # ui.app <-> ui.screens.*, which each need `App` for typing.
        from ui.screens.main_menu import MainMenuScreen

        self.manager.push(MainMenuScreen(self))

    def _create_display(self) -> None:
        flags = pygame.FULLSCREEN if self.settings.fullscreen else 0
        self.screen = pygame.display.set_mode(self.settings.resolution, flags)

    def apply_display_settings(self) -> None:
        """Re-create the display surface after a settings change."""
        self._create_display()
        self.manager.surface = self.screen

    def quit(self) -> None:
        self.running = False

    def run(self) -> None:
        """Blocking main loop. Call once from an entry-point script."""
        while self.running:
            dt = self.clock.tick(FPS) / 1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    continue
                self.manager.handle_event(event)

            self.manager.update(dt)
            self.manager.draw()
            pygame.display.flip()

        pygame.quit()


def main() -> None:  # pragma: no cover -- exercised via manual launch only
    PygameApp().run()


if __name__ == "__main__":  # pragma: no cover
    main()
