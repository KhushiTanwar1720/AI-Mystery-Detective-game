"""
Final accusation screen.

Lists the actual suspects from the active case (`Case.suspects`,
never `Case.correct_suspect`), requires an explicit confirm step, and
only then calls `GameController.conclude_case`, which is the single
real source of the solved/failed outcome, score, and achievement
unlocks -- this screen never guesses or reveals the answer itself.
"""

from __future__ import annotations

import pygame

from ui import theme
from ui.components.button import Button
from ui.screens.base import Screen


class AccusationScreen(Screen):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.pending_suspect: str | None = None
        self.suspect_buttons: list[Button] = []
        self.confirm_button = Button(
            pygame.Rect(0, 0, 260, 50), "CONFIRM ACCUSATION", on_click=self._confirm, enabled=False
        )
        self.cancel_button = Button(pygame.Rect(0, 0, 160, 44), "CANCEL", on_click=self._back)
        self._build()

    def _build(self) -> None:
        case = self.controller.case
        names = list(case.suspects) if case else []

        width, height, gap = 360, 56, 16
        x = (theme.SCREEN_WIDTH - width) // 2
        y = 240

        self.suspect_buttons = []
        for name in names:
            rect = pygame.Rect(x, y, width, height)
            self.suspect_buttons.append(Button(rect, name.upper(), on_click=self._make_selector(name)))
            y += height + gap

        self.confirm_button.rect = pygame.Rect(x, y + 20, width, 50)
        self.cancel_button.rect = pygame.Rect(40, theme.SCREEN_HEIGHT - 70, 160, 44)

    def _make_selector(self, name: str):
        def _select() -> None:
            self.pending_suspect = name
            self.confirm_button.set_enabled(True)

        return _select

    def _confirm(self) -> None:
        if self.pending_suspect is None:
            return
        outcome = self.controller.conclude_case(self.pending_suspect)
        from ui.screens.results_screen import ResultsScreen

        self.manager.replace(ResultsScreen(self.app, outcome))

    def _back(self) -> None:
        self.manager.pop()

    def handle_event(self, event: "pygame.event.Event") -> None:
        for button in self.suspect_buttons:
            button.handle_event(event)
        self.confirm_button.handle_event(event)
        self.cancel_button.handle_event(event)

    def update(self, dt: float) -> None:
        for button in self.suspect_buttons:
            button.update(dt)
        self.confirm_button.update(dt)
        self.cancel_button.update(dt)

    def draw(self, surface: "pygame.Surface") -> None:
        surface.fill(theme.BACKGROUND)
        title = theme.Fonts.heading.render("WHO DO YOU ACCUSE?", True, theme.TEXT_DANGER)
        surface.blit(title, title.get_rect(center=(theme.SCREEN_WIDTH // 2, 160)))

        for button in self.suspect_buttons:
            selected = self.pending_suspect is not None and button.label == self.pending_suspect.upper()
            if selected:
                pygame.draw.rect(surface, theme.ACCENT_BLOOD, button.rect.inflate(6, 6), width=2, border_radius=theme.RADIUS)
            button.draw(surface)

        self.confirm_button.draw(surface)
        self.cancel_button.draw(surface)

        if self.pending_suspect:
            note = theme.Fonts.small.render(
                f"You are about to accuse {self.pending_suspect}. This cannot be undone.",
                True,
                theme.TEXT_MUTED,
            )
            surface.blit(note, note.get_rect(center=(theme.SCREEN_WIDTH // 2, self.confirm_button.rect.bottom + 30)))
