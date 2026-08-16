"""Base Screen class: the lifecycle every UI screen implements."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pygame

    from ui.app import App


class Screen:
    """Base class for every screen (Main Menu, Dashboard, Evidence, ...).

    Screens never talk to the backend directly except through
    `self.app.controller` (a `game.game_controller.GameController`)
    and `self.app.manager` (the `ScreenManager`, for navigation).
    """

    def __init__(self, app: "App") -> None:
        self.app = app
        self.manager = app.manager
        self.controller = app.controller  # game.game_controller.GameController

    # -- Lifecycle hooks, override as needed -------------------------------

    def on_enter(self) -> None:
        """Called once when this screen becomes the active (top) screen."""

    def on_exit(self) -> None:
        """Called once when this screen is popped/replaced off the stack."""

    def on_resume(self) -> None:
        """Called when a screen above this one is popped, returning focus."""

    def handle_event(self, event: "pygame.event.Event") -> None:
        """Called once per pygame event while this screen is active."""

    def update(self, dt: float) -> None:
        """Called once per frame with the elapsed time in seconds."""

    def draw(self, surface: "pygame.Surface") -> None:
        """Called once per frame to render this screen."""
