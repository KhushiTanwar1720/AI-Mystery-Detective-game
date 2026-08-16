"""
Save/Load screen.

Uses only `GameController.save_game`/`load_game`/`list_saves`/
`delete_save` -- no second save system, no direct SaveManager access
from the UI.
"""

from __future__ import annotations

import pygame

from ui import theme
from ui.components.button import Button
from ui.screens.base import Screen

SLOTS = ["slot_1", "slot_2", "slot_3"]


class SaveLoadScreen(Screen):
    def __init__(self, app, mode: str = "save") -> None:
        super().__init__(app)
        self.mode = mode  # "save" or "load"
        self.message = ""
        self.slot_buttons: list[Button] = []
        self.back_button = Button(pygame.Rect(40, theme.SCREEN_HEIGHT - 70, 160, 44), "BACK", on_click=self._back)
        self._build_slot_buttons()

    def _build_slot_buttons(self) -> None:
        width, height, gap = 500, 70, 20
        x = (theme.SCREEN_WIDTH - width) // 2
        y = 160
        self.slot_buttons = []
        for slot in SLOTS:
            rect = pygame.Rect(x, y, width, height)
            self.slot_buttons.append(Button(rect, self._label_for(slot), on_click=self._make_action(slot)))
            y += height + gap

    def _label_for(self, slot: str) -> str:
        info = self.controller.save_manager.get_save_info(slot)
        verb = "SAVE" if self.mode == "save" else "LOAD"
        if info is None:
            return f"{slot.upper()} \u2014 empty ({verb.lower()} here)"
        return (
            f"{slot.upper()} \u2014 {info.get('case_id', '?')} "
            f"\u2022 {info.get('status', '?')} \u2022 score {info.get('score', 0)}"
        )

    def _make_action(self, slot: str):
        def _act() -> None:
            if self.mode == "save":
                success = self.controller.save_game(slot)
                self.message = "Saved." if success else "Nothing to save yet."
            else:
                success = self.controller.load_game(slot)
                if success:
                    from ui.screens.dashboard import DashboardScreen

                    self.manager.replace(DashboardScreen(self.app))
                    return
                self.message = "No save found in that slot."
            self._build_slot_buttons()

        return _act

    def _back(self) -> None:
        self.manager.pop()

    def handle_event(self, event: "pygame.event.Event") -> None:
        for button in self.slot_buttons:
            button.handle_event(event)
        self.back_button.handle_event(event)

    def update(self, dt: float) -> None:
        for button in self.slot_buttons:
            button.update(dt)
        self.back_button.update(dt)

    def draw(self, surface: "pygame.Surface") -> None:
        surface.fill(theme.BACKGROUND)
        heading = "SAVE GAME" if self.mode == "save" else "LOAD GAME"
        surface.blit(theme.Fonts.heading.render(heading, True, theme.ACCENT_GOLD), (40, 40))

        for button in self.slot_buttons:
            button.draw(surface)

        if self.message:
            text = theme.Fonts.small.render(self.message, True, theme.TEXT_SECONDARY)
            surface.blit(text, text.get_rect(center=(theme.SCREEN_WIDTH // 2, 480)))

        self.back_button.draw(surface)
