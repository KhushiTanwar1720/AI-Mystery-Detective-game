"""
Investigation dashboard: the central hub screen a player returns to
between exploring, reviewing evidence/clues/suspects, interrogating,
consulting the AI analyzer, and finally accusing.

All progress numbers come straight from `Investigation.get_progress()`
-- nothing here recomputes evidence/clue/suspect counts itself.
"""

from __future__ import annotations

import pygame

from ui import theme
from ui.components.button import Button
from ui.components.progress_bar import ProgressBar
from ui.screens.base import Screen


class DashboardScreen(Screen):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.evidence_bar = ProgressBar(pygame.Rect(60, 260, 500, 22))
        self.clue_bar = ProgressBar(pygame.Rect(60, 300, 500, 22))
        self.buttons: list[Button] = []
        self._build_buttons()

    def _build_buttons(self) -> None:
        specs = [
            ("EXPLORE", self._explore),
            ("EVIDENCE", self._evidence),
            ("CLUES", self._clues),
            ("SUSPECTS", self._suspects),
            ("INTERROGATE", self._interrogate),
            ("AI ANALYZER", self._ai_analyzer),
            ("ACCUSE", self._accuse),
            ("SAVE", self._save),
            ("MENU", self._menu),
        ]
        width, height, gap = 220, 50, 14
        x = theme.SCREEN_WIDTH - width - 60
        y = 140
        self.buttons = []
        for label, callback in specs:
            rect = pygame.Rect(x, y, width, height)
            self.buttons.append(Button(rect, label, on_click=callback))
            y += height + gap

    def on_enter(self) -> None:
        self._refresh_availability()

    def on_resume(self) -> None:
        self._refresh_availability()

    def _refresh_availability(self) -> None:
        progress = self._progress()
        suspects_available = bool(self.controller.case and self.controller.case.suspects)
        for button in self.buttons:
            if button.label == "INTERROGATE":
                button.set_enabled(suspects_available)
            elif button.label == "ACCUSE":
                button.set_enabled(suspects_available)
            else:
                button.set_enabled(True)

        self.evidence_bar.set_progress(
            progress.get("evidence_discovered", 0), progress.get("evidence_total", 0)
        )
        self.clue_bar.set_progress(
            progress.get("clues_discovered", 0), progress.get("clues_total", 0)
        )

    def _progress(self) -> dict:
        if self.controller.investigation is None:
            return {}
        return self.controller.investigation.get_progress()

    # -- Navigation ---------------------------------------------------------

    def _explore(self) -> None:
        from ui.screens.location_exploration import LocationExplorationScreen

        self.manager.push(LocationExplorationScreen(self.app))

    def _evidence(self) -> None:
        from ui.screens.evidence_screen import EvidenceScreen

        self.manager.push(EvidenceScreen(self.app))

    def _clues(self) -> None:
        from ui.screens.clue_board import ClueBoardScreen

        self.manager.push(ClueBoardScreen(self.app))

    def _suspects(self) -> None:
        from ui.screens.suspect_screen import SuspectScreen

        self.manager.push(SuspectScreen(self.app))

    def _interrogate(self) -> None:
        from ui.screens.suspect_screen import SuspectScreen

        # Interrogation requires picking a suspect first; route
        # through the suspect list rather than duplicating suspect
        # selection here.
        self.manager.push(SuspectScreen(self.app, interrogate_mode=True))

    def _ai_analyzer(self) -> None:
        from ui.screens.ai_analyzer_screen import AIAnalyzerScreen

        self.manager.push(AIAnalyzerScreen(self.app))

    def _accuse(self) -> None:
        from ui.screens.accusation_screen import AccusationScreen

        self.manager.push(AccusationScreen(self.app))

    def _save(self) -> None:
        from ui.screens.save_load_screen import SaveLoadScreen

        self.manager.push(SaveLoadScreen(self.app, mode="save"))

    def _menu(self) -> None:
        from ui.screens.main_menu import MainMenuScreen

        self.manager.clear_to(MainMenuScreen(self.app))

    def handle_event(self, event: "pygame.event.Event") -> None:
        for button in self.buttons:
            button.handle_event(event)

    def update(self, dt: float) -> None:
        for button in self.buttons:
            button.update(dt)

    def draw(self, surface: "pygame.Surface") -> None:
        surface.fill(theme.BACKGROUND)

        case = self.controller.case
        case_title = case.title if case else "No case loaded"
        surface.blit(theme.Fonts.small.render("CASE:", True, theme.TEXT_MUTED), (60, 40))
        surface.blit(theme.Fonts.heading.render(case_title, True, theme.ACCENT_GOLD), (60, 62))

        current_location_id = self.controller.get_current_location_id() if self.controller.investigation else None
        location_name = "Not yet explored"
        if current_location_id:
            location = self.controller.location_manager.get_location(current_location_id)
            if location is not None:
                location_name = location.name

        surface.blit(theme.Fonts.small.render("CURRENT LOCATION:", True, theme.TEXT_MUTED), (60, 130))
        surface.blit(theme.Fonts.body.render(location_name, True, theme.TEXT_PRIMARY), (60, 154))

        progress = self._progress()
        evidence_label = f"Evidence: {progress.get('evidence_discovered', 0)}/{progress.get('evidence_total', 0)}"
        clue_label = f"Clues: {progress.get('clues_discovered', 0)}/{progress.get('clues_total', 0)}"
        self.evidence_bar.draw(surface, label=evidence_label)
        self.clue_bar.draw(surface, label=clue_label)

        suspects_total = progress.get("suspects_total", 0)
        surface.blit(
            theme.Fonts.small.render(f"Suspects: {suspects_total}", True, theme.TEXT_SECONDARY), (60, 340)
        )
        completion = progress.get("completion_percent", 0.0)
        surface.blit(
            theme.Fonts.small.render(f"Investigation progress: {completion}%", True, theme.TEXT_SECONDARY),
            (60, 365),
        )

        for button in self.buttons:
            button.draw(surface)
