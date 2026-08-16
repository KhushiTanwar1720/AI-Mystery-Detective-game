"""
Interrogation screen: dialogue-style interface over the real
`Interrogation` backend (`GameController.ask_question`/`record_answer`/
`end_interrogation`).

The three canned question buttons pose real questions via
`ask_question()`, and record the suspect's own backend-sourced data
(alibi / behavior / relationship_to_victim -- exactly the fields
`Suspect.get_info()` already exposes) as the answer via
`record_answer()`, the same pattern the project's own CLI (`game.app.App`)
uses. No dialogue text is invented beyond the fixed question prompts;
every "answer" shown is real data pulled from the suspect object.
"""

from __future__ import annotations

import pygame

from ui import theme
from ui.components.button import Button
from ui.screens.base import Screen

CANNED_QUESTIONS = [
    ("Ask about timeline", "alibi", "Where were you at the time of the incident?"),
    ("Ask about evidence", "evidence", "Can you explain the evidence found?"),
    ("Ask about another suspect", "relationship", "What do you know about the others involved?"),
]


class InterrogationScreen(Screen):
    def __init__(self, app) -> None:
        super().__init__(app)
        self.suspect_info: dict = {}
        self.transcript: list[tuple[str, str]] = []  # (question_text, answer_text)

        self.question_buttons: list[Button] = []
        self.end_button = Button(
            pygame.Rect(60, theme.SCREEN_HEIGHT - 70, 260, 44), "End interrogation", on_click=self._end
        )
        self._build_question_buttons()

    def _build_question_buttons(self) -> None:
        x, y, width, height, gap = 60, 500, 340, 44, 14
        self.question_buttons = []
        for label, category, text in CANNED_QUESTIONS:
            rect = pygame.Rect(x, y, width, height)
            self.question_buttons.append(Button(rect, label, on_click=self._make_asker(category, text)))
            y += height + gap

    def on_enter(self) -> None:
        interrogation = self.controller.interrogation
        suspect = interrogation.suspect if interrogation else None
        self.suspect_info = suspect.get_info() if suspect is not None else {}
        self.transcript = []

    def _make_asker(self, category: str, text: str):
        def _ask() -> None:
            question = self.controller.ask_question(text, category=category)
            answer = self._backend_answer_for(category)
            self.controller.record_answer(question.question_id, answer)
            self.transcript.append((text, answer))

        return _ask

    def _backend_answer_for(self, category: str) -> str:
        if category == "alibi":
            return self.suspect_info.get("alibi") or "No alibi on record."
        if category == "evidence":
            behavior = self.suspect_info.get("behavior") or []
            return behavior[0] if behavior else (self.suspect_info.get("alibi") or "No comment on record.")
        return self.suspect_info.get("relationship_to_victim") or "No relationship on record."

    def _end(self) -> None:
        self.controller.end_interrogation()
        self.manager.pop()

    def handle_event(self, event: "pygame.event.Event") -> None:
        for button in self.question_buttons:
            button.handle_event(event)
        self.end_button.handle_event(event)

    def update(self, dt: float) -> None:
        for button in self.question_buttons:
            button.update(dt)
        self.end_button.update(dt)

    def draw(self, surface: "pygame.Surface") -> None:
        surface.fill(theme.BACKGROUND)
        surface.blit(theme.Fonts.heading.render("INTERROGATION", True, theme.ACCENT_GOLD), (60, 40))
        surface.blit(
            theme.Fonts.body.render(self.suspect_info.get("name", "Suspect").upper(), True, theme.TEXT_PRIMARY),
            (60, 90),
        )

        y = 140
        for question_text, answer_text in self.transcript[-4:]:
            q_surface = theme.Fonts.small.render(f"Q: {question_text}", True, theme.TEXT_SECONDARY)
            surface.blit(q_surface, (60, y))
            y += 22
            a_surface = theme.Fonts.body.render(f'"{answer_text}"', True, theme.TEXT_PRIMARY)
            surface.blit(a_surface, (60, y))
            y += 34

        for button in self.question_buttons:
            button.draw(surface)
        self.end_button.draw(surface)
