"""
Clue board screen: a visual detective board showing discovered clues,
their related evidence/suspects, and descriptions.

Reads only from `ClueManager`/`Clue.get_info()` -- undiscovered clues
still show as locked entries (id + location only, per `Clue.get_info()`'s
own discovery gating), never leaking clue content early.
"""

from __future__ import annotations

import pygame

from ui import theme
from ui.components.button import Button
from ui.screens.base import Screen


class ClueBoardScreen(Screen):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.back_button = Button(pygame.Rect(40, theme.SCREEN_HEIGHT - 70, 160, 44), "BACK", on_click=self._back)
        self.clue_infos: list[dict] = []

    def on_enter(self) -> None:
        self._refresh()

    def on_resume(self) -> None:
        self._refresh()

    def _refresh(self) -> None:
        case = self.controller.case
        self.clue_infos = []
        if case is None:
            return
        for clue_id in case.clues:
            clue = self.controller.clue_manager.get_clue(clue_id)
            if clue is not None:
                self.clue_infos.append(clue.get_info())

    def _back(self) -> None:
        self.manager.pop()

    def handle_event(self, event: "pygame.event.Event") -> None:
        self.back_button.handle_event(event)

    def update(self, dt: float) -> None:
        self.back_button.update(dt)

    def draw(self, surface: "pygame.Surface") -> None:
        surface.fill(theme.BACKGROUND)
        surface.blit(theme.Fonts.heading.render("CLUE BOARD", True, theme.ACCENT_GOLD), (40, 40))

        y = 110
        for info in self.clue_infos:
            discovered = info.get("discovered", False)
            panel_rect = pygame.Rect(40, y, theme.SCREEN_WIDTH - 80, 90)
            border = theme.ACCENT_GOLD if discovered else theme.LOCKED
            pygame.draw.rect(surface, theme.BACKGROUND_PANEL, panel_rect, border_radius=theme.RADIUS)
            pygame.draw.rect(surface, border, panel_rect, width=1, border_radius=theme.RADIUS)

            if discovered:
                surface.blit(
                    theme.Fonts.body.render(info.get("description", ""), True, theme.TEXT_PRIMARY),
                    (56, y + 10),
                )
                related_evidence = ", ".join(info.get("related_evidence", [])) or "none noted"
                related_suspects = ", ".join(info.get("related_suspects", [])) or "none noted"
                surface.blit(
                    theme.Fonts.small.render(f"Related evidence: {related_evidence}", True, theme.TEXT_SECONDARY),
                    (56, y + 38),
                )
                surface.blit(
                    theme.Fonts.small.render(f"Related suspects: {related_suspects}", True, theme.TEXT_SECONDARY),
                    (56, y + 58),
                )
            else:
                surface.blit(
                    theme.Fonts.body.render(f"Undiscovered clue near {info.get('location', 'unknown')}", True, theme.TEXT_MUTED),
                    (56, y + 32),
                )

            y += 90 + 16

        self.back_button.draw(surface)
