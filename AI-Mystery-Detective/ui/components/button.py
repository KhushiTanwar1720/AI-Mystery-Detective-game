"""Reusable clickable Button component."""

from __future__ import annotations

from typing import Callable, Optional

import pygame

from ui import theme


class Button:
    """A rectangular, hoverable, clickable button with a text label.

    Usage:
        btn = Button(rect, "NEW INVESTIGATION", on_click=lambda: ...)
        btn.handle_event(event)   # per pygame event
        btn.update(dt)            # per frame, for hover-fade animation
        btn.draw(surface)         # per frame
    """

    def __init__(
        self,
        rect: pygame.Rect,
        label: str,
        on_click: Optional[Callable[[], None]] = None,
        enabled: bool = True,
        font=None,
    ) -> None:
        self.rect = pygame.Rect(rect)
        self.label = label
        self.on_click = on_click
        self.enabled = enabled
        self.font = font or theme.Fonts.button

        self._hovered = False
        self._pressed = False
        self._hover_progress = 0.0  # 0..1, animates hover fade in/out

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        if not enabled:
            self._hovered = False
            self._pressed = False

    def handle_event(self, event: "pygame.event.Event") -> bool:
        """Process one pygame event. Returns True if it triggered a click."""
        if not self.enabled:
            return False

        if event.type == pygame.MOUSEMOTION:
            self._hovered = self.rect.collidepoint(event.pos)
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self._pressed = True
            return False

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            was_pressed = self._pressed
            self._pressed = False
            if was_pressed and self.rect.collidepoint(event.pos):
                if self.on_click is not None:
                    self.on_click()
                return True
            return False

        return False

    def update(self, dt: float) -> None:
        target = 1.0 if (self._hovered and self.enabled) else 0.0
        speed = 6.0
        if self._hover_progress < target:
            self._hover_progress = min(target, self._hover_progress + speed * dt)
        elif self._hover_progress > target:
            self._hover_progress = max(target, self._hover_progress - speed * dt)

    def draw(self, surface: "pygame.Surface") -> None:
        if not self.enabled:
            fill = theme.BUTTON_DISABLED
            text_color = theme.TEXT_MUTED
        elif self._pressed:
            fill = theme.BUTTON_PRESSED
            text_color = theme.ACCENT_LANTERN
        else:
            fill = _lerp_color(theme.BUTTON_IDLE, theme.BUTTON_HOVER, self._hover_progress)
            text_color = theme.TEXT_PRIMARY

        pygame.draw.rect(surface, fill, self.rect, border_radius=theme.RADIUS)
        border_color = theme.BUTTON_BORDER if self.enabled else theme.LOCKED
        pygame.draw.rect(surface, border_color, self.rect, width=1, border_radius=theme.RADIUS)

        label_surface = self.font.render(self.label, True, text_color)
        label_rect = label_surface.get_rect(center=self.rect.center)
        surface.blit(label_surface, label_rect)


def _lerp_color(a, b, t: float):
    t = max(0.0, min(1.0, t))
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
