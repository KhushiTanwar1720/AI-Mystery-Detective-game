"""
Player module for AI Mystery Detective.

Defines the `Player` class, which tracks a single player's identity
and investigation progress: which case they're on, what evidence and
clues they've collected, their score, and how many cases they've
solved.

This module is intentionally independent of any UI or storage code.
It knows nothing about how it's displayed or persisted -- callers
(e.g. the future `database` and `ui` modules) are responsible for
that.
"""

from __future__ import annotations

from typing import List, Optional


class Player:
    """Represents a player and their investigation progress.

    Attributes:
        player_id: Unique identifier for the player.
        name: Display name of the player.
        cases_solved: Number of cases the player has completed.
        current_case: ID of the case currently in progress, or None
            if the player isn't investigating anything right now.
        collected_evidence: Evidence items gathered in the current
            case (cleared when a case starts or completes).
        discovered_clues: Clues discovered in the current case
            (cleared when a case starts or completes).
        investigation_score: Cumulative score across all cases.
    """

    def __init__(self, player_id: str, name: str) -> None:
        """Create a new player.

        Args:
            player_id: Unique identifier for the player. Must be a
                non-empty string.
            name: Display name for the player. Must be a non-empty
                string.

        Raises:
            ValueError: If `player_id` or `name` is empty or not a
                string.
        """
        if not isinstance(player_id, str) or not player_id.strip():
            raise ValueError("player_id must be a non-empty string")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("name must be a non-empty string")

        self.player_id: str = player_id
        self.name: str = name
        self.cases_solved: int = 0
        self.current_case: Optional[str] = None
        self.collected_evidence: List[str] = []
        self.discovered_clues: List[str] = []
        self.investigation_score: int = 0

    def start_case(self, case_id: str) -> None:
        """Begin investigating a new case.

        Resets the per-case evidence and clue lists so progress from
        a previous case doesn't bleed into the new one.

        Args:
            case_id: Identifier of the case to start. Must be a
                non-empty string.

        Raises:
            ValueError: If `case_id` is empty or not a string.
            RuntimeError: If a case is already in progress.
        """
        if not isinstance(case_id, str) or not case_id.strip():
            raise ValueError("case_id must be a non-empty string")
        if self.current_case is not None:
            raise RuntimeError(
                f"Cannot start case '{case_id}': "
                f"case '{self.current_case}' is already in progress"
            )

        self.current_case = case_id
        self.collected_evidence = []
        self.discovered_clues = []

    def complete_case(self) -> str:
        """Mark the current case as solved.

        Increments `cases_solved` and clears the active case and its
        per-case evidence/clues.

        Returns:
            The ID of the case that was just completed.

        Raises:
            RuntimeError: If no case is currently in progress.
        """
        if self.current_case is None:
            raise RuntimeError("No case is currently in progress")

        completed_case = self.current_case
        self.cases_solved += 1
        self.current_case = None
        self.collected_evidence = []
        self.discovered_clues = []
        return completed_case

    def add_evidence(self, evidence: str) -> None:
        """Add a piece of evidence to the current case.

        Args:
            evidence: Description or identifier of the evidence.
                Must be a non-empty string.

        Raises:
            ValueError: If `evidence` is empty or not a string.
            RuntimeError: If no case is currently in progress.
        """
        if not isinstance(evidence, str) or not evidence.strip():
            raise ValueError("evidence must be a non-empty string")
        if self.current_case is None:
            raise RuntimeError("Cannot add evidence: no case in progress")

        if evidence not in self.collected_evidence:
            self.collected_evidence.append(evidence)

    def add_clue(self, clue: str) -> None:
        """Add a discovered clue to the current case.

        Args:
            clue: Description or identifier of the clue. Must be a
                non-empty string.

        Raises:
            ValueError: If `clue` is empty or not a string.
            RuntimeError: If no case is currently in progress.
        """
        if not isinstance(clue, str) or not clue.strip():
            raise ValueError("clue must be a non-empty string")
        if self.current_case is None:
            raise RuntimeError("Cannot add clue: no case in progress")

        if clue not in self.discovered_clues:
            self.discovered_clues.append(clue)

    def update_score(self, points: int) -> None:
        """Adjust the player's investigation score.

        Args:
            points: Number of points to add. May be negative to
                apply a penalty, but the resulting score is floored
                at 0.

        Raises:
            ValueError: If `points` is not an integer.
        """
        if not isinstance(points, int) or isinstance(points, bool):
            raise ValueError("points must be an integer")

        self.investigation_score = max(0, self.investigation_score + points)

    def get_progress(self) -> dict:
        """Return a snapshot of the player's current progress.

        Returns:
            A dictionary summarizing the player's state: id, name,
            cases solved, current case, evidence/clue counts, and
            score. Useful for UI or save-game code without exposing
            internal mutable lists directly.
        """
        return {
            "player_id": self.player_id,
            "name": self.name,
            "cases_solved": self.cases_solved,
            "current_case": self.current_case,
            "evidence_count": len(self.collected_evidence),
            "clues_count": len(self.discovered_clues),
            "investigation_score": self.investigation_score,
        }

    def __repr__(self) -> str:
        return (
            f"Player(player_id={self.player_id!r}, name={self.name!r}, "
            f"cases_solved={self.cases_solved}, "
            f"investigation_score={self.investigation_score})"
        )
