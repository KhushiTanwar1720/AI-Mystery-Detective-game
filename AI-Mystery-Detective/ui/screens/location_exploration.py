"""
Location exploration screen.

Built entirely on the existing id-based Location integration:
`GameController.get_available_locations()` /
`GameController.explore_location_by_id()` /
`GameController.get_location_info()` /
`GameController.get_visited_location_ids()`. This screen never tracks
its own visited/visit-count state -- `Location` remains the single
authoritative source, exactly as the backend design requires.
"""

from __future__ import annotations

import pygame

from ui import theme
from ui.components.button import Button
from ui.components.cards import LocationCard
from ui.environment_renderer import render_environment
from ui.environments import resolve_environment, spec_for, stable_seed
from ui.screens.base import Screen


class LocationExplorationScreen(Screen):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.current_location_id = None
        self.current_info: dict = {}
        self.connection_cards: list[LocationCard] = []

        self.back_button = Button(pygame.Rect(40, theme.SCREEN_HEIGHT - 70, 160, 44), "BACK", on_click=self._back)
        self.inspect_button = Button(
            pygame.Rect(220, theme.SCREEN_HEIGHT - 70, 220, 44), "INSPECT AREA", on_click=self._inspect
        )
        self.discover_evidence_button = Button(
            pygame.Rect(460, theme.SCREEN_HEIGHT - 70, 260, 44),
            "SEARCH FOR CLUES",
            on_click=self._discover_all_here,
        )
        self.message = ""

    def on_enter(self) -> None:
        self._enter_starting_location()

    def on_resume(self) -> None:
        self._refresh()

    def _enter_starting_location(self) -> None:
        current_id = self.controller.get_current_location_id()
        if current_id is None:
            locations = self.controller.get_available_locations()
            if locations:
                current_id = locations[0].location_id
        if current_id is not None:
            self._go_to(current_id)
        else:
            self.current_location_id = None
            self.current_info = {}

    def _go_to(self, location_id: str) -> None:
        try:
            self.current_info = self.controller.explore_location_by_id(location_id)
        except (KeyError, RuntimeError, ValueError) as exc:
            self.message = str(exc)
            return
        self.current_location_id = location_id
        self.message = ""
        self._build_connection_cards()

    def _refresh(self) -> None:
        if self.current_location_id is not None:
            self.current_info = self.controller.get_location_info(self.current_location_id)
        self._build_connection_cards()

    def _build_connection_cards(self) -> None:
        connected = self.current_info.get("connected_locations", [])
        visited_ids = set(self.controller.get_visited_location_ids())

        self.connection_cards = []
        x, y = 60, 460
        width, height, gap = 220, 46, 12
        for connected_id in connected:
            location = self.controller.location_manager.get_location(connected_id)
            name = location.name if location is not None else connected_id
            rect = pygame.Rect(x, y, width, height)
            self.connection_cards.append(
                LocationCard(
                    rect,
                    name,
                    visited=connected_id in visited_ids,
                    on_click=self._make_mover(connected_id),
                )
            )
            y += height + gap

    def _make_mover(self, location_id: str):
        def _move() -> None:
            self._go_to(location_id)

        return _move

    def _inspect(self) -> None:
        if self.current_location_id is not None:
            self.current_info = self.controller.get_location_info(self.current_location_id)

    def _discover_all_here(self) -> None:
        if self.current_location_id is None:
            return
        for evidence_info in self.current_info.get("evidence_here", []):
            if not evidence_info.get("discovered"):
                try:
                    self.controller.discover_evidence(evidence_info["evidence_id"])
                except (KeyError, RuntimeError):
                    pass
        for clue_info in self.current_info.get("clues_here", []):
            if not clue_info.get("discovered"):
                try:
                    self.controller.discover_clue(clue_info["clue_id"])
                except (KeyError, RuntimeError):
                    pass
        self.current_info = self.controller.get_location_info(self.current_location_id)

    def _back(self) -> None:
        self.manager.pop()

    def handle_event(self, event: "pygame.event.Event") -> None:
        self.back_button.handle_event(event)
        self.inspect_button.handle_event(event)
        self.discover_evidence_button.handle_event(event)
        for card in self.connection_cards:
            card.handle_event(event)

    def update(self, dt: float) -> None:
        self.back_button.update(dt)
        self.inspect_button.update(dt)
        self.discover_evidence_button.update(dt)

    def draw(self, surface: "pygame.Surface") -> None:
        location = None
        if self.current_location_id is not None:
            location = self.controller.location_manager.get_location(self.current_location_id)

        horror_rating = self._current_horror_rating()
        palette = theme.palette_for(horror_rating)

        if location is None:
            surface.fill(palette.background)
            message = self.message or "No locations available for this case yet."
            text = theme.Fonts.body.render(message, True, theme.TEXT_MUTED)
            surface.blit(text, text.get_rect(center=(theme.SCREEN_WIDTH // 2, 300)))
            self.back_button.draw(surface)
            return

        case_title = self.controller.case.title if self.controller.case else ""
        environment_id = resolve_environment(location.name, case_title)
        env_spec = spec_for(environment_id)
        render_environment(
            surface,
            env_spec,
            seed=stable_seed(self.current_location_id),
            horror_fog_alpha=palette.vignette_alpha,
            flicker=palette.flicker,
        )

        # A semi-transparent text panel keeps location name/description/
        # buttons readable regardless of how busy the environment
        # backdrop behind them is.
        panel = pygame.Surface((theme.SCREEN_WIDTH, 260), pygame.SRCALPHA)
        panel.fill((*theme.BACKGROUND, 190))
        surface.blit(panel, (0, 0))

        name_surface = theme.Fonts.heading.render(location.name.upper(), True, theme.ACCENT_GOLD)
        surface.blit(name_surface, (60, 50))

        description = location.description
        for i, line in enumerate(_wrap(description, theme.Fonts.body, theme.SCREEN_WIDTH - 120)):
            text = theme.Fonts.body.render(line, True, theme.TEXT_SECONDARY)
            surface.blit(text, (60, 110 + i * 26))

        ambient = theme.Fonts.small.render(palette.ambient_text, True, theme.TEXT_MUTED)
        surface.blit(ambient, (60, 190))

        visit_count = self.current_info.get("visit_count", location.visit_count)
        surface.blit(
            theme.Fonts.small.render(f"Visits: {visit_count}", True, theme.TEXT_MUTED), (60, 220)
        )

        evidence_here = self.current_info.get("evidence_here", [])
        clues_here = self.current_info.get("clues_here", [])

        # Bottom info/action panel -- keeps the evidence/clue summary,
        # connection cards, and buttons readable over the environment
        # backdrop, while leaving a clear vertical band (roughly
        # y=260..400) where the environment itself is fully visible.
        bottom_panel_y = 400
        bottom_panel = pygame.Surface((theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT - bottom_panel_y), pygame.SRCALPHA)
        bottom_panel.fill((*theme.BACKGROUND, 190))
        surface.blit(bottom_panel, (0, bottom_panel_y))

        surface.blit(
            theme.Fonts.small.render(
                f"Evidence here: {sum(1 for e in evidence_here if e.get('discovered'))}/{len(evidence_here)}"
                f"   Clues here: {sum(1 for c in clues_here if c.get('discovered'))}/{len(clues_here)}",
                True,
                theme.TEXT_SECONDARY,
            ),
            (60, 420),
        )

        if self.connection_cards:
            surface.blit(
                theme.Fonts.small.render("CONNECTED LOCATIONS:", True, theme.TEXT_MUTED), (60, 430)
            )
        for card in self.connection_cards:
            card.draw(surface)

        if self.message:
            surface.blit(theme.Fonts.small.render(self.message, True, theme.TEXT_DANGER), (60, theme.SCREEN_HEIGHT - 110))

        self.back_button.draw(surface)
        self.inspect_button.draw(surface)
        self.discover_evidence_button.draw(surface)

    def _current_horror_rating(self) -> int:
        # The case-selection level metadata carries the horror rating;
        # the dashboard/exploration screens don't own campaign data
        # themselves, so this falls back to a calm default (1) if no
        # campaign level maps to the active case (e.g. a case started
        # directly, bypassing case selection, as in tests).
        from ui.campaign import load_campaign

        case = self.controller.case
        if case is None:
            return 1
        levels = load_campaign(self.controller.case_manager.cases_dir)
        for level in levels:
            if level.case_id == case.case_id:
                return level.horror_rating
        return 1


def _wrap(text: str, font, max_width: int, max_lines: int = 2):
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
