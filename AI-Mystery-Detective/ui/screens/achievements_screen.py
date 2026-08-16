"""Achievement gallery screen, backed entirely by AchievementManager."""

from __future__ import annotations

import pygame

from ui import theme
from ui.components.button import Button
from ui.components.cards import AchievementCard
from ui.screens.base import Screen

COLUMNS = 2
CARD_WIDTH = 560
CARD_HEIGHT = 90
GAP = 16


class AchievementsScreen(Screen):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.cards: list[AchievementCard] = []
        self.back_button = Button(pygame.Rect(40, theme.SCREEN_HEIGHT - 70, 160, 44), "BACK", on_click=self._back)

    def on_enter(self) -> None:
        self._build_cards()

    def _build_cards(self) -> None:
        achievements = self.controller.get_achievements()
        start_x = (theme.SCREEN_WIDTH - (COLUMNS * CARD_WIDTH + (COLUMNS - 1) * GAP)) // 2
        start_y = 140

        self.cards = []
        for index, achievement in enumerate(achievements):
            row, col = divmod(index, COLUMNS)
            rect = pygame.Rect(
                start_x + col * (CARD_WIDTH + GAP), start_y + row * (CARD_HEIGHT + GAP), CARD_WIDTH, CARD_HEIGHT
            )
            self.cards.append(
                AchievementCard(rect, achievement.name, achievement.description, achievement.unlocked)
            )

    def _back(self) -> None:
        self.manager.pop()

    def handle_event(self, event: "pygame.event.Event") -> None:
        self.back_button.handle_event(event)

    def update(self, dt: float) -> None:
        self.back_button.update(dt)

    def draw(self, surface: "pygame.Surface") -> None:
        surface.fill(theme.BACKGROUND)
        surface.blit(theme.Fonts.heading.render("ACHIEVEMENTS", True, theme.ACCENT_GOLD), (40, 40))

        progress = self.controller.get_achievement_progress()
        subtitle = f"{progress.get('unlocked_count', 0)}/{progress.get('total_count', 0)} unlocked ({progress.get('completion_percent', 0)}%)"
        surface.blit(theme.Fonts.small.render(subtitle, True, theme.TEXT_SECONDARY), (40, 90))

        for card in self.cards:
            card.draw(surface)

        self.back_button.draw(surface)
