"""
Campaign-style case/level selection screen.

Entirely data-driven: pulls its level list from `ui.campaign.load_campaign`,
which in turn resolves real backend availability/status from
`GameController.case_manager`/`GameController.player`. Adding a new
case to the campaign means adding a `data/campaign.json` entry (and,
separately, real case/evidence/clue/location/suspect data files) --
never touching this screen's code.
"""

from __future__ import annotations

import pygame

from ui import theme
from ui.campaign import load_campaign
from ui.components.button import Button
from ui.components.cards import CaseCard
from ui.screens.base import Screen

COLUMNS = 3
CARD_WIDTH = 360
CARD_HEIGHT = 150
GAP = 24


class CaseSelectionScreen(Screen):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.cards: list[CaseCard] = []
        self.back_button = Button(
            pygame.Rect(40, theme.SCREEN_HEIGHT - 70, 160, 44), "BACK", on_click=self._back
        )
        self.scroll_y = 0
        self._max_scroll = 0

    def on_enter(self) -> None:
        levels = load_campaign(
            cases_dir=self.controller.case_manager.cases_dir,
            player=self.controller.player,
            case_manager=self.controller.case_manager,
        )

        start_x = (theme.SCREEN_WIDTH - (COLUMNS * CARD_WIDTH + (COLUMNS - 1) * GAP)) // 2
        start_y = 140

        self.cards = []
        for index, level in enumerate(levels):
            row, col = divmod(index, COLUMNS)
            x = start_x + col * (CARD_WIDTH + GAP)
            y = start_y + row * (CARD_HEIGHT + GAP)
            rect = pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT)
            self.cards.append(
                CaseCard(rect, level, on_click=self._make_selector(level))
            )

        rows = (len(levels) + COLUMNS - 1) // COLUMNS
        content_bottom = start_y + rows * (CARD_HEIGHT + GAP)
        self._max_scroll = max(0, content_bottom - (theme.SCREEN_HEIGHT - 120))
        self.scroll_y = 0

    def _make_selector(self, level):
        def _select() -> None:
            if not level.is_playable() or not level.case_id:
                return
            self.controller.load_case(level.case_id)
            self.controller.start_investigation()
            from ui.screens.dashboard import DashboardScreen

            self.manager.push(DashboardScreen(self.app))

        return _select

    def _back(self) -> None:
        self.manager.pop()

    def handle_event(self, event: "pygame.event.Event") -> None:
        self.back_button.handle_event(event)

        if event.type == pygame.MOUSEWHEEL:
            self.scroll_y = max(0, min(self._max_scroll, self.scroll_y - event.y * 40))
            return

        # Cards are drawn scroll-offset, so translate mouse events the
        # same amount before hit-testing them.
        translated = event
        if event.type in (pygame.MOUSEMOTION, pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP):
            pos = (event.pos[0], event.pos[1] + self.scroll_y)
            translated = pygame.event.Event(event.type, {**event.dict, "pos": pos})

        for card in self.cards:
            card.handle_event(translated)

    def update(self, dt: float) -> None:
        self.back_button.update(dt)

    def draw(self, surface: "pygame.Surface") -> None:
        surface.fill(theme.BACKGROUND)

        title = theme.Fonts.heading.render("CASE FILES", True, theme.ACCENT_GOLD)
        surface.blit(title, (40, 40))

        playable_count = sum(1 for c in self.cards if c.level.has_backend_data)
        subtitle = theme.Fonts.small.render(
            f"{playable_count} case(s) currently playable \u2022 {len(self.cards)} planned",
            True,
            theme.TEXT_SECONDARY,
        )
        surface.blit(subtitle, (40, 90))

        # Clip and scroll-offset the card area.
        clip_rect = pygame.Rect(0, 120, theme.SCREEN_WIDTH, theme.SCREEN_HEIGHT - 200)
        previous_clip = surface.get_clip()
        surface.set_clip(clip_rect)
        for card in self.cards:
            offset_rect = card.rect.move(0, -self.scroll_y)
            original_rect = card.rect
            card.rect = offset_rect
            card.draw(surface)
            card.rect = original_rect
        surface.set_clip(previous_clip)

        self.back_button.draw(surface)
