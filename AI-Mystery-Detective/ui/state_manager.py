"""
Stack-based screen manager for UI navigation.

`ScreenManager` owns a stack of `Screen` instances (see
`ui.screens.base.Screen`). `push()` opens a new screen on top (e.g.
Dashboard -> Evidence), `pop()` returns to the previous one (e.g.
Evidence -> back to Dashboard), and `replace()` swaps the current top
screen without growing the stack (e.g. Main Menu -> Case Selection,
where "back" from Case Selection should return to Main Menu, not to
whatever was briefly on top before).

A short cross-fade plays on every push/pop/replace, matching the
"subtle fade transitions" requirement without needing any per-screen
transition code.
"""

from __future__ import annotations

from typing import List, Optional

import pygame

from ui import theme

FADE_DURATION = 0.25  # seconds


class ScreenManager:
    def __init__(self, surface: "pygame.Surface") -> None:
        self.surface = surface
        self._stack: List["Screen"] = []  # noqa: F821 -- Screen imported lazily to avoid a cycle
        self._fade_alpha = 0.0
        self._fade_direction = 0  # -1 fading out old, +1 fading in new
        self._fade_surface = pygame.Surface(surface.get_size())
        self._fade_surface.fill(theme.BACKGROUND)

    @property
    def current(self) -> Optional["Screen"]:  # noqa: F821
        return self._stack[-1] if self._stack else None

    def push(self, screen: "Screen") -> None:  # noqa: F821
        self._stack.append(screen)
        screen.on_enter()
        self._start_fade()

    def pop(self) -> Optional["Screen"]:  # noqa: F821
        if not self._stack:
            return None
        leaving = self._stack.pop()
        leaving.on_exit()
        if self.current is not None:
            self.current.on_resume()
        self._start_fade()
        return leaving

    def replace(self, screen: "Screen") -> None:  # noqa: F821
        if self._stack:
            leaving = self._stack.pop()
            leaving.on_exit()
        self._stack.append(screen)
        screen.on_enter()
        self._start_fade()

    def clear_to(self, screen: "Screen") -> None:  # noqa: F821
        """Replace the entire stack with a single screen (e.g. Main Menu)."""
        while self._stack:
            self._stack.pop().on_exit()
        self._stack.append(screen)
        screen.on_enter()
        self._start_fade()

    def _start_fade(self) -> None:
        self._fade_alpha = 255.0
        self._fade_direction = -1

    def handle_event(self, event: "pygame.event.Event") -> None:
        if self.current is not None:
            self.current.handle_event(event)

    def update(self, dt: float) -> None:
        if self.current is not None:
            self.current.update(dt)

        if self._fade_direction != 0:
            step = (255.0 / FADE_DURATION) * dt
            self._fade_alpha += self._fade_direction * step
            if self._fade_alpha <= 0:
                self._fade_alpha = 0
                self._fade_direction = 0

    def draw(self) -> None:
        self.surface.fill(theme.BACKGROUND)
        if self.current is not None:
            self.current.draw(self.surface)

        if self._fade_alpha > 0:
            self._fade_surface.set_alpha(int(self._fade_alpha))
            self.surface.blit(self._fade_surface, (0, 0))
