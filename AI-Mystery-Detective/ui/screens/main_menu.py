"""Main menu screen: entry point of the game."""

from __future__ import annotations

import pygame

from ui import theme
from ui.components.button import Button
from ui.screens.base import Screen


class MainMenuScreen(Screen):
    TITLE = "AI MYSTERY DETECTIVE"

    def __init__(self, app) -> None:
        super().__init__(app)
        self.buttons: list[Button] = []
        self._build_buttons()

    def _build_buttons(self) -> None:
        labels = [
            ("NEW INVESTIGATION", self._new_investigation),
            ("CONTINUE", self._continue),
            ("CASE FILES", self._case_files),
            ("DETECTIVE PROFILE", self._profile),
            ("ACHIEVEMENTS", self._achievements),
            ("SETTINGS", self._settings),
            ("EXIT", self._exit),
        ]
        width, height, gap = 320, 50, 14
        start_x = (theme.SCREEN_WIDTH - width) // 2
        start_y = 300

        self.buttons = []
        for i, (label, callback) in enumerate(labels):
            rect = pygame.Rect(start_x, start_y + i * (height + gap), width, height)
            self.buttons.append(Button(rect, label, on_click=callback))

    def on_enter(self) -> None:
        has_save = self.controller.has_save("slot_1")
        for button in self.buttons:
            if button.label == "CONTINUE":
                button.set_enabled(has_save)

    def _new_investigation(self) -> None:
        from ui.screens.case_selection import CaseSelectionScreen

        self.manager.push(CaseSelectionScreen(self.app))

    def _continue(self) -> None:
        if self.controller.load_game("slot_1"):
            from ui.screens.dashboard import DashboardScreen

            self.manager.push(DashboardScreen(self.app))

    def _case_files(self) -> None:
        from ui.screens.case_selection import CaseSelectionScreen

        self.manager.push(CaseSelectionScreen(self.app))

    def _profile(self) -> None:
        from ui.screens.profile_screen import ProfileScreen

        self.manager.push(ProfileScreen(self.app))

    def _achievements(self) -> None:
        from ui.screens.achievements_screen import AchievementsScreen

        self.manager.push(AchievementsScreen(self.app))

    def _settings(self) -> None:
        from ui.screens.settings_screen import SettingsScreen

        self.manager.push(SettingsScreen(self.app))

    def _exit(self) -> None:
        self.app.quit()

    def handle_event(self, event: "pygame.event.Event") -> None:
        for button in self.buttons:
            button.handle_event(event)

    def update(self, dt: float) -> None:
        for button in self.buttons:
            button.update(dt)

    def draw(self, surface: "pygame.Surface") -> None:
        surface.fill(theme.BACKGROUND)

        title_surface = theme.Fonts.title.render(self.TITLE, True, theme.ACCENT_GOLD)
        title_rect = title_surface.get_rect(center=(theme.SCREEN_WIDTH // 2, 160))
        surface.blit(title_surface, title_rect)

        subtitle = theme.Fonts.small.render(
            "A case-driven investigation, powered by AI analysis.", True, theme.TEXT_SECONDARY
        )
        subtitle_rect = subtitle.get_rect(center=(theme.SCREEN_WIDTH // 2, 210))
        surface.blit(subtitle, subtitle_rect)

        for button in self.buttons:
            button.draw(surface)
