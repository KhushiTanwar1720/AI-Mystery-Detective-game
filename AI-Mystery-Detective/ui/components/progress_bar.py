"""Reusable ProgressBar component."""

from __future__ import annotations

import pygame

from ui import theme


class ProgressBar:
    """A horizontal fraction-of-completion bar with an optional label."""

    def __init__(self, rect: pygame.Rect, fill_color=None) -> None:
        self.rect = pygame.Rect(rect)
        self.fill_color = fill_color or theme.ACCENT_GOLD
        self.fraction = 0.0  # 0..1

    def set_progress(self, completed: int, total: int) -> None:
        self.fraction = 0.0 if total <= 0 else max(0.0, min(1.0, completed / total))

    def draw(self, surface: "pygame.Surface", label: str = "") -> None:
        pygame.draw.rect(surface, theme.BACKGROUND_PANEL_LIGHT, self.rect, border_radius=theme.RADIUS)
        pygame.draw.rect(surface, theme.BORDER, self.rect, width=1, border_radius=theme.RADIUS)

        fill_width = int(self.rect.width * self.fraction)
        if fill_width > 0:
            fill_rect = pygame.Rect(self.rect.x, self.rect.y, fill_width, self.rect.height)
            pygame.draw.rect(surface, self.fill_color, fill_rect, border_radius=theme.RADIUS)

        if label:
            text_surface = theme.Fonts.small.render(label, True, theme.TEXT_PRIMARY)
            text_rect = text_surface.get_rect(center=self.rect.center)
            surface.blit(text_surface, text_rect)
