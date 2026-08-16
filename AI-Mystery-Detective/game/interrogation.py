"""
Interrogation module for AI Mystery Detective.

Defines three classes:

- `Question`: a single question posed to a suspect.
- `Statement`: a suspect's recorded answer to a `Question`.
- `Interrogation`: manages a single questioning session with a
  suspect -- selecting them, asking questions, recording their
  answers, reviewing the session's history, and flagging basic
  contradictions between their answers.

This module is intentionally independent of any UI or AI code. It
does not generate questions, judge truthfulness, or render anything
-- it only models a questioning session and enforces valid action
sequencing. Question generation and deeper contradiction analysis are
left to a future `ai` module; this module only detects the simplest
case, where a suspect gives two different answers to the same (or a
re-asked) question.

It integrates with `game.suspect.Suspect`: every recorded answer is
also appended to the suspect's own `statements` list via
`Suspect.add_statement`, so the suspect's profile stays in sync with
what's been said during interrogation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from game.suspect import Suspect, SuspectManager

# Valid lifecycle states for an Interrogation. Mirrors the pattern
# used by `game.investigation.VALID_INVESTIGATION_STATUSES`.
VALID_INTERROGATION_STATUSES = ("not_started", "active", "ended")

# Loose, non-exhaustive set of question categories. Kept open-ended
# (any non-empty string is accepted) so new categories can be added
# without changing this module, similar to `Case.crime_type` /
# `Evidence.evidence_type`.
DEFAULT_QUESTION_CATEGORY = "general"


class Question:
    """Represents a single question posed to a suspect.

    A `Question` is a lightweight data-holding object. It does not
    know how to generate itself (that's a future `ai` concern) or how
    it will be displayed -- it just tracks its own text, category,
    and whether it has been answered yet.
    """

    def __init__(
        self,
        question_id: str,
        text: str,
        category: str = DEFAULT_QUESTION_CATEGORY,
        answered: bool = False,
    ) -> None:
        """Create a new question.

        Args:
            question_id: Unique identifier for this question (unique
                within its interrogation session).
            text: The question text itself.
            category: Loose grouping label (e.g. "alibi",
                "relationship", "behavior"). Defaults to "general".
            answered: Whether this question has already been
                answered. Defaults to False.

        Raises:
            ValueError: If `question_id`, `text`, or `category` is
                empty or not a string.
        """
        for field_name, value in (
            ("question_id", question_id),
            ("text", text),
            ("category", category),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")

        if not isinstance(answered, bool):
            raise ValueError("answered must be a boolean")

        self.question_id: str = question_id
        self.text: str = text
        self.category: str = category
        self.answered: bool = answered

    def mark_answered(self) -> None:
        """Mark this question as having been answered.

        Raises:
            RuntimeError: If the question has already been answered.
        """
        if self.answered:
            raise RuntimeError(
                f"Question '{self.question_id}' has already been answered"
            )
        self.answered = True

    def is_answered(self) -> bool:
        """Return whether this question has been answered."""
        return self.answered

    def get_info(self) -> Dict[str, Any]:
        """Return this question's data as a plain dictionary."""
        return {
            "question_id": self.question_id,
            "text": self.text,
            "category": self.category,
            "answered": self.answered,
        }

    def __repr__(self) -> str:
        return (
            f"Question(question_id={self.question_id!r}, "
            f"category={self.category!r}, answered={self.answered})"
        )


class Statement:
    """Represents a suspect's recorded answer to a `Question`.

    A `Statement` links a specific answer back to the question that
    prompted it (by id and text, not by object reference, so it stays
    a simple, JSON-friendly data holder like `Evidence`/`Clue`) and
    to the suspect who gave it.
    """

    def __init__(
        self,
        statement_id: str,
        suspect_id: str,
        question_id: str,
        question_text: str,
        answer: str,
        timestamp: Optional[str] = None,
    ) -> None:
        """Create a new statement.

        Args:
            statement_id: Unique identifier for this statement
                (unique within its interrogation session).
            suspect_id: Id of the suspect who gave this answer.
            question_id: Id of the `Question` this answers.
            question_text: Text of the question this answers (copied
                in at creation time so the statement is
                self-contained even if the question object changes).
            answer: The suspect's answer text.
            timestamp: UTC ISO-8601 timestamp of when the answer was
                recorded. Defaults to "now" if omitted.

        Raises:
            ValueError: If any required string field is empty/not a
                string.
        """
        for field_name, value in (
            ("statement_id", statement_id),
            ("suspect_id", suspect_id),
            ("question_id", question_id),
            ("question_text", question_text),
            ("answer", answer),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")

        self.statement_id: str = statement_id
        self.suspect_id: str = suspect_id
        self.question_id: str = question_id
        self.question_text: str = question_text
        self.answer: str = answer
        self.timestamp: str = timestamp or datetime.now(timezone.utc).isoformat()

    def get_info(self) -> Dict[str, Any]:
        """Return this statement's data as a plain dictionary."""
        return {
            "statement_id": self.statement_id,
            "suspect_id": self.suspect_id,
            "question_id": self.question_id,
            "question_text": self.question_text,
            "answer": self.answer,
            "timestamp": self.timestamp,
        }

    def __repr__(self) -> str:
        return (
            f"Statement(statement_id={self.statement_id!r}, "
            f"suspect_id={self.suspect_id!r}, question_id={self.question_id!r})"
        )


class Interrogation:
    """Manages a single questioning session with one suspect.

    An `Interrogation` does not own suspect data directly -- it holds
    a reference to a `SuspectManager` and coordinates the session
    against it:

    - `select_suspect` / `start_interrogation` choose and begin a
      session with a suspect.
    - `ask_question` records a new question being posed.
    - `record_answer` records the suspect's answer to a specific
      question, and mirrors it onto `Suspect.add_statement` so the
      suspect's own profile stays up to date.
    - `compare_statements` scans recorded statements for basic
      contradictions -- cases where the suspect gave differing
      answers to the same (or a re-asked, same-text) question.
    - `get_history` reports the full session action log.
    - `end_interrogation` closes out the session and returns a
      summary, including any contradictions found.

    All actions are validated: invalid input raises `ValueError`,
    actions taken in the wrong state raise `RuntimeError`, and
    references to unknown suspects/questions raise `KeyError`.
    """

    def __init__(
        self,
        suspect_manager: SuspectManager,
        interrogator: str = "Detective",
    ) -> None:
        """Create a new interrogation session.

        Args:
            suspect_manager: Source of `Suspect` objects to question.
            interrogator: Display name of whoever is conducting the
                interrogation. Defaults to "Detective".

        Raises:
            ValueError: If `interrogator` is empty or not a string.
        """
        if not isinstance(interrogator, str) or not interrogator.strip():
            raise ValueError("interrogator must be a non-empty string")

        self.suspect_manager: SuspectManager = suspect_manager
        self.interrogator: str = interrogator

        self.suspect: Optional[Suspect] = None
        self.status: str = "not_started"

        self._questions: List[Question] = []
        self._statements: List[Statement] = []
        self._history: List[Dict[str, Any]] = []
        self._question_counter: int = 0
        self._statement_counter: int = 0

    # -- Internal helpers ---------------------------------------------------

    def _log(self, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Append an entry to the interrogation's action history."""
        self._history.append(
            {
                "action": action,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": dict(details) if details else {},
            }
        )

    def _require_suspect_selected(self) -> Suspect:
        if self.suspect is None:
            raise RuntimeError(
                "No suspect selected; call select_suspect() first"
            )
        return self.suspect

    def _require_active(self) -> Suspect:
        if self.status != "active" or self.suspect is None:
            raise RuntimeError(
                "No active interrogation; call start_interrogation() first"
            )
        return self.suspect

    @staticmethod
    def _require_nonempty_str(value: Any, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must be a non-empty string")
        return value

    def _next_question_id(self) -> str:
        self._question_counter += 1
        return f"q{self._question_counter}"

    def _next_statement_id(self) -> str:
        self._statement_counter += 1
        return f"s{self._statement_counter}"

    def _find_question(self, question_id: str) -> Question:
        for question in self._questions:
            if question.question_id == question_id:
                return question
        raise KeyError(
            f"No question with id '{question_id}' was asked in this session"
        )

    # -- Suspect selection & lifecycle ----------------------------------

    def select_suspect(self, suspect_id: str) -> Suspect:
        """Choose which suspect this interrogation will question.

        Selecting a suspect does not start the session -- call
        `start_interrogation()` afterwards (or pass `suspect_id`
        directly to `start_interrogation`).

        Args:
            suspect_id: Id of a suspect registered with
                `suspect_manager`.

        Returns:
            The selected `Suspect`.

        Raises:
            ValueError: If `suspect_id` is empty or not a string.
            RuntimeError: If an interrogation is already active (end
                it first before switching suspects).
            KeyError: If no suspect with that id is registered.
        """
        self._require_nonempty_str(suspect_id, "suspect_id")
        if self.status == "active":
            raise RuntimeError(
                "Cannot select a new suspect while an interrogation is "
                "active; call end_interrogation() first"
            )

        suspect = self.suspect_manager.get_suspect(suspect_id)
        if suspect is None:
            raise KeyError(f"No suspect found with id '{suspect_id}'")

        self.suspect = suspect
        self._log("select_suspect", {"suspect_id": suspect_id})
        return suspect

    def start_interrogation(self, suspect_id: Optional[str] = None) -> Suspect:
        """Begin the interrogation, optionally selecting a suspect first.

        Args:
            suspect_id: If given, selects this suspect (via
                `select_suspect`) before starting. If omitted, a
                suspect must already have been selected.

        Returns:
            The `Suspect` now being interrogated.

        Raises:
            ValueError: If `suspect_id` is given but invalid.
            RuntimeError: If no suspect is selected, an interrogation
                is already active, or this session has already ended.
            KeyError: If `suspect_id` is given but not found.
        """
        if suspect_id is not None:
            self.select_suspect(suspect_id)

        suspect = self._require_suspect_selected()

        if self.status == "active":
            raise RuntimeError("Interrogation is already active")
        if self.status == "ended":
            raise RuntimeError(
                "This interrogation has already ended; "
                "create a new Interrogation to start again"
            )

        self.status = "active"
        self._questions = []
        self._statements = []
        self._question_counter = 0
        self._statement_counter = 0
        self._log("start_interrogation", {"suspect_id": suspect.suspect_id})
        return suspect

    # -- Questions ------------------------------------------------------------

    def ask_question(
        self, text: str, category: str = DEFAULT_QUESTION_CATEGORY
    ) -> Question:
        """Pose a new question to the suspect being interrogated.

        Args:
            text: The question text.
            category: Loose grouping label for the question (e.g.
                "alibi", "relationship", "behavior"). Defaults to
                "general".

        Returns:
            The newly created (unanswered) `Question`.

        Raises:
            ValueError: If `text` or `category` is empty or not a
                string.
            RuntimeError: If no interrogation is currently active.
        """
        self._require_active()
        self._require_nonempty_str(text, "text")
        self._require_nonempty_str(category, "category")

        question = Question(
            question_id=self._next_question_id(), text=text, category=category
        )
        self._questions.append(question)
        self._log(
            "ask_question",
            {"question_id": question.question_id, "text": text, "category": category},
        )
        return question

    # -- Answers / statements ---------------------------------------------

    def record_answer(self, question_id: str, answer: str) -> Statement:
        """Record the suspect's answer to a previously asked question.

        The answer is also appended to the suspect's own
        `statements` list via `Suspect.add_statement`, keeping the
        suspect's profile in sync with what was said in this
        interrogation.

        Args:
            question_id: Id of a question asked earlier in this
                session (via `ask_question`).
            answer: The suspect's answer text.

        Returns:
            The newly created `Statement`.

        Raises:
            ValueError: If `question_id` or `answer` is empty or not
                a string.
            RuntimeError: If no interrogation is active, or the
                question has already been answered.
            KeyError: If no question with that id was asked in this
                session.
        """
        suspect = self._require_active()
        self._require_nonempty_str(question_id, "question_id")
        self._require_nonempty_str(answer, "answer")

        question = self._find_question(question_id)
        if question.is_answered():
            raise RuntimeError(
                f"Question '{question_id}' has already been answered"
            )

        question.mark_answered()

        statement = Statement(
            statement_id=self._next_statement_id(),
            suspect_id=suspect.suspect_id,
            question_id=question.question_id,
            question_text=question.text,
            answer=answer,
        )
        self._statements.append(statement)
        suspect.add_statement(answer)

        self._log(
            "record_answer",
            {
                "question_id": question_id,
                "statement_id": statement.statement_id,
                "answer": answer,
            },
        )
        return statement

    # -- Contradiction detection --------------------------------------------

    def compare_statements(self) -> List[Dict[str, Any]]:
        """Scan recorded statements for basic contradictions.

        This is intentionally simple: statements are grouped by their
        question's normalized text (case-insensitive, trimmed), and
        any group where the suspect gave two or more differing
        answers (also compared case-insensitively) is flagged as a
        contradiction. Deeper semantic contradiction analysis (e.g.
        an alibi that conflicts with a *different* question's answer)
        is left to a future `ai` module.

        Returns:
            A list of contradiction records, each with the shared
            question text and the conflicting statements (as plain
            dictionaries via `Statement.get_info()`). Empty if no
            contradictions were found. Safe to call at any time,
            including after the interrogation has ended.
        """
        groups: Dict[str, List[Statement]] = {}
        for statement in self._statements:
            key = statement.question_text.strip().lower()
            groups.setdefault(key, []).append(statement)

        contradictions: List[Dict[str, Any]] = []
        for statements in groups.values():
            distinct_answers = {s.answer.strip().lower() for s in statements}
            if len(distinct_answers) > 1:
                contradictions.append(
                    {
                        "question_text": statements[0].question_text,
                        "statements": [s.get_info() for s in statements],
                    }
                )

        self._log(
            "compare_statements", {"contradictions_found": len(contradictions)}
        )
        return contradictions

    # -- History --------------------------------------------------------------

    def get_history(self) -> List[Dict[str, Any]]:
        """Return the full, chronologically ordered action history.

        Each entry records the action name, a UTC ISO-8601 timestamp,
        and action-specific details (e.g. which question was asked).
        Includes actions like `select_suspect` that happen before the
        session becomes "active".

        Returns:
            A copy of the internal history log (safe to mutate
            without affecting the interrogation).
        """
        return [dict(entry) for entry in self._history]

    def get_questions(self) -> List[Question]:
        """Return all questions asked so far in this session, in order."""
        return list(self._questions)

    def get_statements(self) -> List[Statement]:
        """Return all statements recorded so far in this session, in order."""
        return list(self._statements)

    # -- Ending -------------------------------------------------------------

    def end_interrogation(self) -> Dict[str, Any]:
        """End the current interrogation session.

        Returns:
            A dictionary summarizing the session: `suspect_id`,
            number of questions asked, number of answers recorded,
            and any contradictions found (via `compare_statements`).

        Raises:
            RuntimeError: If no interrogation is currently active.
        """
        suspect = self._require_active()

        contradictions = self.compare_statements()
        unanswered = [q.question_id for q in self._questions if not q.is_answered()]

        outcome = {
            "suspect_id": suspect.suspect_id,
            "questions_asked": len(self._questions),
            "answers_recorded": len(self._statements),
            "unanswered_questions": unanswered,
            "contradictions": contradictions,
        }

        self.status = "ended"
        self._log("end_interrogation", outcome)
        return outcome

    def __repr__(self) -> str:
        suspect_id = self.suspect.suspect_id if self.suspect is not None else None
        return (
            f"Interrogation(suspect_id={suspect_id!r}, status={self.status!r}, "
            f"interrogator={self.interrogator!r})"
        )
