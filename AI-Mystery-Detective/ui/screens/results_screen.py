"""
Result screen: shown immediately after `GameController.conclude_case`.

Every number here comes from the `outcome` dict `conclude_case`
returned (itself built from `ScoreManager.get_score_summary()`,
`Investigation.get_progress()`, and the achievement ids
`AchievementManager.check_achievements` newly unlocked) -- nothing is
recomputed independently.
"""

from __future__ import annotations

import pygame

from ui import theme
from ui.components.button import Button
from ui.screens.base import Screen


class ResultsScreen(Screen):
    def __init__(self, app, outcome: dict) -> None:
        super().__init__(app)
        self.outcome = outcome
        self.next_button = Button(pygame.Rect(0, 0, 220, 50), "NEXT LEVEL", on_click=self._next_level)
        self.case_files_button = Button(pygame.Rect(0, 0, 220, 50), "CASE FILES", on_click=self._case_files)
        self.menu_button = Button(pygame.Rect(0, 0, 220, 50), "MAIN MENU", on_click=self._menu)
        self._layout_buttons()

    def _layout_buttons(self) -> None:
        width, height, gap = 220, 50, 20
        total_width = width * 3 + gap * 2
        x = (theme.SCREEN_WIDTH - total_width) // 2
        y = theme.SCREEN_HEIGHT - 120
        self.next_button.rect = pygame.Rect(x, y, width, height)
        self.case_files_button.rect = pygame.Rect(x + width + gap, y, width, height)
        self.menu_button.rect = pygame.Rect(x + 2 * (width + gap), y, width, height)

    def _next_level(self) -> None:
        from ui.screens.case_selection import CaseSelectionScreen

        self.manager.clear_to(CaseSelectionScreen(self.app))

    def _case_files(self) -> None:
        from ui.screens.case_selection import CaseSelectionScreen

        self.manager.clear_to(CaseSelectionScreen(self.app))

    def _menu(self) -> None:
        from ui.screens.main_menu import MainMenuScreen

        self.manager.clear_to(MainMenuScreen(self.app))

    def handle_event(self, event: "pygame.event.Event") -> None:
        self.next_button.handle_event(event)
        self.case_files_button.handle_event(event)
        self.menu_button.handle_event(event)

    def update(self, dt: float) -> None:
        self.next_button.update(dt)
        self.case_files_button.update(dt)
        self.menu_button.update(dt)

    def draw(self, surface: "pygame.Surface") -> None:
        surface.fill(theme.BACKGROUND)

        solved = self.outcome.get("solved", False)
        heading = "CASE SOLVED" if solved else "CASE FAILED"
        color = theme.TEXT_SUCCESS if solved else theme.TEXT_DANGER
        title = theme.Fonts.title.render(heading, True, color)
        surface.blit(title, title.get_rect(center=(theme.SCREEN_WIDTH // 2, 100)))

        score_info = self.outcome.get("score_info", {})
        progress = self.outcome.get("progress", {})

        lines = [
            f"SCORE: {score_info.get('score', 0)}",
            f"ACCURACY: {score_info.get('accuracy', 0)}%",
            f"RANK: {score_info.get('rank', 'Detective Rookie')}",
            f"Evidence discovered: {progress.get('evidence_discovered', 0)}/{progress.get('evidence_total', 0)}",
            f"Clues discovered: {progress.get('clues_discovered', 0)}/{progress.get('clues_total', 0)}",
            f"Suspects examined: {progress.get('suspects_examined', 0)}/{progress.get('suspects_total', 0)}",
        ]

        y = 200
        for line in lines:
            surface.blit(theme.Fonts.body.render(line, True, theme.TEXT_PRIMARY), (theme.SCREEN_WIDTH // 2 - 220, y))
            y += 34

        unlocked = self.outcome.get("achievements_unlocked", [])
        if unlocked:
            y += 10
            surface.blit(
                theme.Fonts.small.render("ACHIEVEMENTS UNLOCKED", True, theme.ACCENT_GOLD),
                (theme.SCREEN_WIDTH // 2 - 220, y),
            )
            y += 24
            achievements_by_id = {a.achievement_id: a for a in self.controller.get_achievements()}
            for achievement_id in unlocked:
                achievement = achievements_by_id.get(achievement_id)
                label = achievement.name if achievement else achievement_id
                surface.blit(
                    theme.Fonts.small.render(f"\U0001F3C6 {label}", True, theme.TEXT_PRIMARY),
                    (theme.SCREEN_WIDTH // 2 - 220, y),
                )
                y += 22

        self.next_button.draw(surface)
        self.case_files_button.draw(surface)
        self.menu_button.draw(surface)
