"""
Reusable "card" components: small bordered summary tiles used across
the case-selection, location-exploration, evidence, suspect, and
achievements screens.

Every card is a pure presentation object -- it takes already-resolved
display data (a `LevelInfo`, a dict from `Location.get_location_info()`,
`Evidence.get_info()`, etc., or an `Achievement`) and never reaches
back into `GameController`/backend modules itself. Screens are
responsible for fetching that data and constructing cards from it.
"""

from __future__ import annotations

from typing import Callable, Optional

import pygame

from ui import theme
from ui.campaign import LEVEL_STATUS_LOCKED, LEVEL_STATUS_NOT_YET_BUILT, LevelInfo


class CaseCard:
    """Campaign level tile for the case-selection screen."""

    def __init__(self, rect: pygame.Rect, level: LevelInfo, on_click: Optional[Callable[[], None]] = None) -> None:
        self.rect = pygame.Rect(rect)
        self.level = level
        self.on_click = on_click
        self._hovered = False

    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self._hovered = self.rect.collidepoint(event.pos)
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos) and self.level.is_playable():
                if self.on_click is not None:
                    self.on_click()
                return True
        return False

    def draw(self, surface: "pygame.Surface") -> None:
        locked = self.level.status in (LEVEL_STATUS_LOCKED, LEVEL_STATUS_NOT_YET_BUILT)

        fill = theme.BACKGROUND_PANEL_LIGHT if (self._hovered and not locked) else theme.BACKGROUND_PANEL
        border = theme.LOCKED if locked else theme.ACCENT_GOLD

        pygame.draw.rect(surface, fill, self.rect, border_radius=theme.RADIUS)
        pygame.draw.rect(surface, border, self.rect, width=1, border_radius=theme.RADIUS)

        pad = theme.PADDING_SM
        x = self.rect.x + pad
        y = self.rect.y + pad

        level_label = f"LEVEL {self.level.level_number:02d}"
        level_color = theme.TEXT_MUTED if locked else theme.ACCENT_GOLD
        surface.blit(theme.Fonts.small.render(level_label, True, level_color), (x, y))
        y += 22

        title_color = theme.TEXT_MUTED if locked else theme.TEXT_PRIMARY
        surface.blit(theme.Fonts.body.render(self.level.title, True, title_color), (x, y))
        y += 26

        if self.level.subtitle:
            surface.blit(theme.Fonts.small.render(self.level.subtitle, True, theme.TEXT_SECONDARY), (x, y))
            y += 20

        stars_color = theme.TEXT_MUTED if locked else theme.ACCENT_GOLD
        surface.blit(
            theme.Fonts.small.render(f"Difficulty: {self.level.difficulty_display()}", True, stars_color),
            (x, y),
        )
        y += 18
        surface.blit(
            theme.Fonts.small.render(f"Horror: {self.level.horror_display()}", True, theme.TEXT_DANGER if not locked else theme.TEXT_MUTED),
            (x, y),
        )
        y += 22

        status_text = {
            LEVEL_STATUS_LOCKED: "LOCKED",
            LEVEL_STATUS_NOT_YET_BUILT: "COMING SOON",
        }.get(self.level.status, self.level.status.upper().replace("_", " "))
        status_color = theme.TEXT_SUCCESS if self.level.status == "completed" else theme.TEXT_MUTED
        surface.blit(theme.Fonts.small.render(status_text, True, status_color), (x, y))


class LocationCard:
    """A connected-location tile shown during location exploration."""

    def __init__(self, rect: pygame.Rect, name: str, visited: bool, on_click: Optional[Callable[[], None]] = None) -> None:
        self.rect = pygame.Rect(rect)
        self.name = name
        self.visited = visited
        self.on_click = on_click
        self._hovered = False

    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self._hovered = self.rect.collidepoint(event.pos)
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.on_click is not None:
                    self.on_click()
                return True
        return False

    def draw(self, surface: "pygame.Surface") -> None:
        fill = theme.BACKGROUND_PANEL_LIGHT if self._hovered else theme.BACKGROUND_PANEL
        pygame.draw.rect(surface, fill, self.rect, border_radius=theme.RADIUS)
        pygame.draw.rect(surface, theme.BORDER_LIGHT, self.rect, width=1, border_radius=theme.RADIUS)

        label = self.name + ("  \u2713" if self.visited else "")
        color = theme.TEXT_SECONDARY if self.visited else theme.TEXT_PRIMARY
        text_surface = theme.Fonts.small.render(label, True, color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)


class EvidenceCard:
    """A single evidence item tile for the evidence screen."""

    def __init__(self, rect: pygame.Rect, evidence_info: dict) -> None:
        self.rect = pygame.Rect(rect)
        self.info = evidence_info

    def draw(self, surface: "pygame.Surface") -> None:
        discovered = self.info.get("discovered", False)
        border = theme.ACCENT_GOLD if discovered else theme.LOCKED
        pygame.draw.rect(surface, theme.BACKGROUND_PANEL, self.rect, border_radius=theme.RADIUS)
        pygame.draw.rect(surface, border, self.rect, width=1, border_radius=theme.RADIUS)

        pad = theme.PADDING_SM
        x, y = self.rect.x + pad, self.rect.y + pad

        if discovered:
            name = self.info.get("name", self.info.get("evidence_id", "Evidence"))
            surface.blit(theme.Fonts.body.render(name, True, theme.TEXT_PRIMARY), (x, y))
            y += 26
            description = self.info.get("description", "")
            for line in _wrap_text(description, theme.Fonts.small, self.rect.width - 2 * pad):
                surface.blit(theme.Fonts.small.render(line, True, theme.TEXT_SECONDARY), (x, y))
                y += 18
            found_at = self.info.get("location_found")
            if found_at:
                surface.blit(
                    theme.Fonts.small.render(f"Found: {found_at}", True, theme.TEXT_MUTED), (x, self.rect.bottom - pad - 16)
                )
        else:
            surface.blit(theme.Fonts.body.render("Undiscovered", True, theme.TEXT_MUTED), (x, y))


class SuspectCard:
    """A suspect summary tile for the suspect screen."""

    def __init__(self, rect: pygame.Rect, suspect_info: dict, on_click: Optional[Callable[[], None]] = None) -> None:
        self.rect = pygame.Rect(rect)
        self.info = suspect_info
        self.on_click = on_click
        self._hovered = False

    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEMOTION:
            self._hovered = self.rect.collidepoint(event.pos)
            return False
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if self.on_click is not None:
                    self.on_click()
                return True
        return False

    def draw(self, surface: "pygame.Surface") -> None:
        fill = theme.BACKGROUND_PANEL_LIGHT if self._hovered else theme.BACKGROUND_PANEL
        pygame.draw.rect(surface, fill, self.rect, border_radius=theme.RADIUS)
        pygame.draw.rect(surface, theme.BORDER_LIGHT, self.rect, width=1, border_radius=theme.RADIUS)

        pad = theme.PADDING_SM
        x, y = self.rect.x + pad, self.rect.y + pad
        surface.blit(theme.Fonts.body.render(self.info.get("name", "Suspect"), True, theme.TEXT_PRIMARY), (x, y))
        y += 24
        occupation = self.info.get("occupation")
        if occupation:
            surface.blit(theme.Fonts.small.render(occupation, True, theme.TEXT_SECONDARY), (x, y))
            y += 18
        suspicion = self.info.get("suspicion_level")
        if suspicion is not None:
            surface.blit(
                theme.Fonts.small.render(f"Suspicion: {suspicion}", True, theme.TEXT_DANGER), (x, y)
            )


class AchievementCard:
    """An achievement tile for the achievements gallery screen."""

    def __init__(self, rect: pygame.Rect, name: str, description: str, unlocked: bool) -> None:
        self.rect = pygame.Rect(rect)
        self.name = name
        self.description = description
        self.unlocked = unlocked

    def draw(self, surface: "pygame.Surface") -> None:
        border = theme.ACCENT_GOLD if self.unlocked else theme.LOCKED
        pygame.draw.rect(surface, theme.BACKGROUND_PANEL, self.rect, border_radius=theme.RADIUS)
        pygame.draw.rect(surface, border, self.rect, width=1, border_radius=theme.RADIUS)

        pad = theme.PADDING_SM
        x, y = self.rect.x + pad, self.rect.y + pad

        icon = "\U0001F3C6" if self.unlocked else "\U0001F512"
        name_color = theme.ACCENT_GOLD if self.unlocked else theme.TEXT_MUTED
        surface.blit(theme.Fonts.body.render(f"{icon} {self.name}", True, name_color), (x, y))
        y += 26

        desc_color = theme.TEXT_SECONDARY if self.unlocked else theme.TEXT_MUTED
        for line in _wrap_text(self.description, theme.Fonts.small, self.rect.width - 2 * pad):
            surface.blit(theme.Fonts.small.render(line, True, desc_color), (x, y))
            y += 18


def _wrap_text(text: str, font, max_width: int, max_lines: int = 3):
    """Greedy word-wrap `text` to fit `max_width`, capped at `max_lines`."""
    if not text:
        return []

    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    return lines
