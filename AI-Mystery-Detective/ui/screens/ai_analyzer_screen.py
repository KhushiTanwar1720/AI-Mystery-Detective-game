"""
AI Analyzer screen: a dedicated "AI Detective" panel over the real
`AIAnalyzer` (`GameController.run_ai_analysis`).

Presents evidence/clue counts, suspicion scores, contradictions, and
a narrative summary exactly as `AnalysisResult`/`generate_investigation_summary`
returns them -- the AI assists (surfaces patterns, flags
contradictions, offers hints) but the final accusation decision is
always left to the player on the separate Accusation screen.
"""

from __future__ import annotations

import pygame

from ui import theme
from ui.components.button import Button
from ui.screens.base import Screen


class AIAnalyzerScreen(Screen):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.result_data: dict = {}
        self.error: str = ""
        self.back_button = Button(pygame.Rect(40, theme.SCREEN_HEIGHT - 70, 160, 44), "BACK", on_click=self._back)
        self.run_button = Button(
            pygame.Rect(220, theme.SCREEN_HEIGHT - 70, 260, 44), "RUN ANALYSIS", on_click=self._run
        )

    def on_enter(self) -> None:
        self._run()

    def _run(self) -> None:
        if self.controller.case is None:
            self.error = "No active case to analyze."
            return
        try:
            result = self.controller.run_ai_analysis(include_hints=True)
            self.result_data = result.data
            self.error = ""
        except RuntimeError as exc:
            self.error = str(exc)

    def _back(self) -> None:
        self.manager.pop()

    def handle_event(self, event: "pygame.event.Event") -> None:
        self.back_button.handle_event(event)
        self.run_button.handle_event(event)

    def update(self, dt: float) -> None:
        self.back_button.update(dt)
        self.run_button.update(dt)

    def draw(self, surface: "pygame.Surface") -> None:
        surface.fill(theme.BACKGROUND)
        surface.blit(theme.Fonts.heading.render("AI DETECTIVE ANALYSIS", True, theme.ACCENT_GOLD), (40, 40))

        if self.error:
            surface.blit(theme.Fonts.body.render(self.error, True, theme.TEXT_DANGER), (40, 100))
            self.back_button.draw(surface)
            self.run_button.draw(surface)
            return

        progress = self.result_data.get("progress", {})
        y = 100
        lines = [
            f"Evidence considered: {progress.get('evidence_discovered', 0)}/{progress.get('evidence_total', 0)}",
            f"Clues considered: {progress.get('clues_discovered', 0)}/{progress.get('clues_total', 0)}",
            f"Suspects with statements: {progress.get('suspects_with_statements', 0)}/{progress.get('suspects_total', 0)}",
        ]
        for line in lines:
            surface.blit(theme.Fonts.body.render(line, True, theme.TEXT_SECONDARY), (40, y))
            y += 28

        y += 10
        surface.blit(theme.Fonts.small.render("SUSPICION RANKING", True, theme.TEXT_MUTED), (40, y))
        y += 24
        scores = self.result_data.get("suspicion_scores", {}).get("data", {}).get("scores", [])
        for entry in scores[:5]:
            name = entry.get("name", "Unknown")
            score = entry.get("score", entry.get("suspicion_score", "?"))
            surface.blit(
                theme.Fonts.small.render(f"\u2022 {name} \u2014 suspicion {score}", True, theme.TEXT_PRIMARY),
                (56, y),
            )
            y += 20

        y += 10
        surface.blit(theme.Fonts.small.render("CONTRADICTIONS", True, theme.TEXT_MUTED), (40, y))
        y += 24
        contradictions = self.result_data.get("inconsistencies", {}).get("data", {}).get("inconsistencies", [])
        if contradictions:
            for c in contradictions[:4]:
                text = c.get("detail") or str(c)
                surface.blit(theme.Fonts.small.render(f"\u2022 {text}", True, theme.TEXT_DANGER), (56, y))
                y += 20
        else:
            surface.blit(theme.Fonts.small.render("None detected so far.", True, theme.TEXT_SECONDARY), (56, y))
            y += 20

        narrative = self.result_data.get("narrative", "")
        if narrative:
            y += 10
            surface.blit(theme.Fonts.small.render("SUMMARY", True, theme.TEXT_MUTED), (40, y))
            y += 24
            for line in _wrap(narrative, theme.Fonts.small, theme.SCREEN_WIDTH - 120, max_lines=3):
                surface.blit(theme.Fonts.small.render(line, True, theme.TEXT_PRIMARY), (56, y))
                y += 20

        self.back_button.draw(surface)
        self.run_button.draw(surface)


def _wrap(text: str, font, max_width: int, max_lines: int = 3):
    if not text:
        return []
    words = text.split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
        if len(lines) >= max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    return lines
