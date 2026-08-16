"""
Suspect screen: professional suspect profile listing.

Also doubles as the interrogation entry point (`interrogate_mode=True`)
-- selecting a suspect card either opens their profile detail, or (in
interrogate mode) starts a real `Interrogation` via
`GameController.start_interrogation` and pushes `InterrogationScreen`.

Never displays `Case.correct_suspect` -- suspect data comes only from
`Suspect.get_info()`, which has no such field.
"""

from __future__ import annotations

import pygame

from ui import theme
from ui.components.button import Button
from ui.components.cards import SuspectCard
from ui.screens.base import Screen

COLUMNS = 3
CARD_WIDTH = 360
CARD_HEIGHT = 130
GAP = 20


class SuspectScreen(Screen):
    def __init__(self, app, interrogate_mode: bool = False) -> None:
        super().__init__(app)
        self.interrogate_mode = interrogate_mode
        self.cards: list[SuspectCard] = []
        self.selected_info: dict | None = None
        self.back_button = Button(pygame.Rect(40, theme.SCREEN_HEIGHT - 70, 160, 44), "BACK", on_click=self._back)

    def on_enter(self) -> None:
        self._build_cards()

    def on_resume(self) -> None:
        self._build_cards()
        self.selected_info = None

    def _build_cards(self) -> None:
        suspects = self.controller.get_case_suspects() if self.controller.case else []
        start_x = (theme.SCREEN_WIDTH - (COLUMNS * CARD_WIDTH + (COLUMNS - 1) * GAP)) // 2
        start_y = 130

        self.cards = []
        for index, suspect in enumerate(suspects):
            row, col = divmod(index, COLUMNS)
            rect = pygame.Rect(
                start_x + col * (CARD_WIDTH + GAP), start_y + row * (CARD_HEIGHT + GAP), CARD_WIDTH, CARD_HEIGHT
            )
            self.cards.append(
                SuspectCard(rect, suspect.get_info(), on_click=self._make_selector(suspect))
            )

    def _make_selector(self, suspect):
        def _select() -> None:
            self.controller.examine_suspect(suspect.suspect_id)
            if self.interrogate_mode:
                from ui.screens.interrogation_screen import InterrogationScreen

                self.controller.start_interrogation(suspect.suspect_id)
                self.manager.push(InterrogationScreen(self.app))
            else:
                self.selected_info = suspect.get_info()

        return _select

    def _back(self) -> None:
        self.manager.pop()

    def handle_event(self, event: "pygame.event.Event") -> None:
        self.back_button.handle_event(event)
        for card in self.cards:
            card.handle_event(event)

    def update(self, dt: float) -> None:
        self.back_button.update(dt)

    def draw(self, surface: "pygame.Surface") -> None:
        surface.fill(theme.BACKGROUND)
        heading = "SELECT A SUSPECT TO INTERROGATE" if self.interrogate_mode else "SUSPECTS"
        surface.blit(theme.Fonts.heading.render(heading, True, theme.ACCENT_GOLD), (40, 40))

        for card in self.cards:
            card.draw(surface)

        if self.selected_info is not None:
            self._draw_detail(surface, self.selected_info)

        self.back_button.draw(surface)

    def _draw_detail(self, surface: "pygame.Surface", info: dict) -> None:
        panel_rect = pygame.Rect(200, 500, theme.SCREEN_WIDTH - 400, 240)
        pygame.draw.rect(surface, theme.BACKGROUND_PANEL, panel_rect, border_radius=theme.RADIUS)
        pygame.draw.rect(surface, theme.ACCENT_GOLD, panel_rect, width=1, border_radius=theme.RADIUS)

        x, y = panel_rect.x + 20, panel_rect.y + 16
        surface.blit(theme.Fonts.body.render(info.get("name", ""), True, theme.TEXT_PRIMARY), (x, y))
        y += 30
        surface.blit(
            theme.Fonts.small.render(
                f"{info.get('occupation', '')} \u2022 Age {info.get('age', '?')} \u2022 {info.get('relationship_to_victim', '')}",
                True,
                theme.TEXT_SECONDARY,
            ),
            (x, y),
        )
        y += 26
        surface.blit(theme.Fonts.small.render(info.get("description", ""), True, theme.TEXT_SECONDARY), (x, y))
        y += 26
        surface.blit(
            theme.Fonts.small.render(f"Suspicion level: {info.get('suspicion_level', 0)}", True, theme.TEXT_DANGER),
            (x, y),
        )
