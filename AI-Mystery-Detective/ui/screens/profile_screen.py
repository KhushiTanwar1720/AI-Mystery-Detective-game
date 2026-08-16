"""Detective profile screen: Player/GameState/ScoreManager summary."""

from __future__ import annotations

import pygame

from ui import theme
from ui.components.button import Button
from ui.screens.base import Screen


class ProfileScreen(Screen):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.back_button = Button(pygame.Rect(40, theme.SCREEN_HEIGHT - 70, 160, 44), "BACK", on_click=self._back)

    def _back(self) -> None:
        self.manager.pop()

    def handle_event(self, event: "pygame.event.Event") -> None:
        self.back_button.handle_event(event)

    def update(self, dt: float) -> None:
        self.back_button.update(dt)

    def draw(self, surface: "pygame.Surface") -> None:
        surface.fill(theme.BACKGROUND)
        surface.blit(theme.Fonts.heading.render("DETECTIVE PROFILE", True, theme.ACCENT_GOLD), (40, 40))

        player = self.controller.player
        score_summary = self.controller.score_manager.get_score_summary()
        achievement_progress = self.controller.get_achievement_progress()

        lines = [
            f"Name: {player.name}",
            f"Rank: {score_summary.get('rank', 'Detective Rookie')}",
            f"Total score: {score_summary.get('score', 0)}",
            f"Cases completed: {player.cases_solved}",
            f"Accuracy: {score_summary.get('accuracy', 0)}%",
            f"Evidence discovered: {len(player.collected_evidence)}",
            f"Clues discovered: {len(player.discovered_clues)}",
            f"Achievements: {achievement_progress.get('unlocked_count', 0)}/{achievement_progress.get('total_count', 0)}",
        ]

        y = 120
        for line in lines:
            surface.blit(theme.Fonts.body.render(line, True, theme.TEXT_PRIMARY), (60, y))
            y += 34

        self.back_button.draw(surface)
