"""Evidence screen: displays every evidence item belonging to the active case."""

from __future__ import annotations

import pygame

from ui import theme
from ui.components.button import Button
from ui.components.cards import EvidenceCard
from ui.screens.base import Screen

COLUMNS = 3
CARD_WIDTH = 360
CARD_HEIGHT = 150
GAP = 20


class EvidenceScreen(Screen):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.cards: list[EvidenceCard] = []
        self.back_button = Button(pygame.Rect(40, theme.SCREEN_HEIGHT - 70, 160, 44), "BACK", on_click=self._back)

    def on_enter(self) -> None:
        self._build_cards()

    def on_resume(self) -> None:
        self._build_cards()

    def _build_cards(self) -> None:
        case = self.controller.case
        self.cards = []
        if case is None:
            return

        start_x = (theme.SCREEN_WIDTH - (COLUMNS * CARD_WIDTH + (COLUMNS - 1) * GAP)) // 2
        start_y = 130

        for index, evidence_id in enumerate(case.evidence):
            evidence = self.controller.evidence_manager.get_evidence(evidence_id)
            if evidence is None:
                continue
            row, col = divmod(index, COLUMNS)
            rect = pygame.Rect(
                start_x + col * (CARD_WIDTH + GAP), start_y + row * (CARD_HEIGHT + GAP), CARD_WIDTH, CARD_HEIGHT
            )
            self.cards.append(EvidenceCard(rect, evidence.get_info()))

    def _back(self) -> None:
        self.manager.pop()

    def handle_event(self, event: "pygame.event.Event") -> None:
        self.back_button.handle_event(event)

    def update(self, dt: float) -> None:
        self.back_button.update(dt)

    def draw(self, surface: "pygame.Surface") -> None:
        surface.fill(theme.BACKGROUND)
        surface.blit(theme.Fonts.heading.render("EVIDENCE", True, theme.ACCENT_GOLD), (40, 40))

        discovered = sum(1 for c in self.cards if c.info.get("discovered"))
        surface.blit(
            theme.Fonts.small.render(f"{discovered}/{len(self.cards)} discovered", True, theme.TEXT_SECONDARY),
            (40, 90),
        )

        for card in self.cards:
            card.draw(surface)

        self.back_button.draw(surface)
