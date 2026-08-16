"""Reusable Panel component: a bordered rectangular content container."""

from __future__ import annotations

import pygame

from ui import theme


class Panel:
    """A simple bordered background panel other components render on top of."""

    def __init__(self, rect: pygame.Rect, fill=None, border=None, radius: int = theme.RADIUS) -> None:
        self.rect = pygame.Rect(rect)
        self.fill = fill or theme.BACKGROUND_PANEL
        self.border = border or theme.BORDER
        self.radius = radius

    def draw(self, surface: "pygame.Surface") -> None:
        pygame.draw.rect(surface, self.fill, self.rect, border_radius=self.radius)
        pygame.draw.rect(surface, self.border, self.rect, width=1, border_radius=self.radius)
