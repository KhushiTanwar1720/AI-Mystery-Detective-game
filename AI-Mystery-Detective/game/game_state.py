"""
GameState module for AI Mystery Detective.

Defines the `GameState` class, which manages and coordinates the runtime state
of an active game session and mystery case.

`GameState` coordinates session data across `Case`, `Player`, `Investigation`,
`Interrogation`, and `ScoreManager` without duplicating their business logic.
It is serialization-friendly for future SaveManager persistence.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from game.case import Case
    from game.investigation import Investigation
    from game.interrogation import Interrogation
    from game.player import Player

VALID_GAME_STATUSES = ("not_started", "active", "completed")


class GameState:
    """Tracks and coordinates active game session state.

    Attributes:
        player: Active Player instance.
        case: Active Case instance.
        investigation: Active Investigation instance.
        interrogation: Current or latest Interrogation instance.
        current_suspect_id: ID of the currently selected suspect, if any.
        discovered_evidence: List of discovered evidence IDs (deduplicated).
        discovered_clues: List of discovered clue IDs (deduplicated).
        interrogation_history: History log of interrogation outcomes.
        hints_used: Count of hints requested during the active case.
        unnecessary_actions: Count of redundant actions taken.
        score: Current calculated score.
        accuracy: Current calculated accuracy percentage (0.0 to 100.0).
        rank: Current player rank title.
        status: Lifecycle status of the current game state ("not_started", "active", "completed").
        outcome: Final case outcome summary once completed.
    """

    def __init__(self, player: Optional[Player] = None) -> None:
        """Initialize GameState.

        Args:
            player: Optional Player instance to register at creation.
        """
        self.player: Optional[Player] = player
        self.case: Optional[Case] = None
        self.investigation: Optional[Investigation] = None
        self.interrogation: Optional[Interrogation] = None
        self.current_suspect_id: Optional[str] = None

        self.discovered_evidence: List[str] = []
        self.discovered_clues: List[str] = []
        self.interrogation_history: List[Dict[str, Any]] = []

        self.hints_used: int = 0
        self.unnecessary_actions: int = 0
        self.score: int = 0
        self.accuracy: float = 0.0
        self.rank: str = "Detective Rookie"

        self.status: str = "not_started"
        self.outcome: Optional[Dict[str, Any]] = None

    def start_game(self, player: Player) -> None:
        """Start a new game session with a Player.

        Args:
            player: Player object. Must not be None.

        Raises:
            ValueError: If `player` is None or invalid.
        """
        if player is None or not hasattr(player, "player_id"):
            raise ValueError("player must be a valid Player instance")

        self.reset_state()
        self.player = player

    def start_case(self, case: Case, investigation: Optional[Investigation] = None) -> None:
        """Set up active state for a new case and investigation.

        Args:
            case: Case instance being investigated.
            investigation: Optional Investigation instance.

        Raises:
            ValueError: If `case` is None or invalid.
        """
        if case is None or not hasattr(case, "case_id"):
            raise ValueError("case must be a valid Case instance")

        self.case = case
        self.investigation = investigation
        self.interrogation = None
        self.current_suspect_id = None

        self.discovered_evidence = []
        self.discovered_clues = []
        self.interrogation_history = []

        self.hints_used = 0
        self.unnecessary_actions = 0
        self.score = 0
        self.accuracy = 0.0
        self.rank = "Detective Rookie"

        self.status = "active"
        self.outcome = None

    def end_case(self, outcome: Dict[str, Any]) -> None:
        """Mark the active case as completed and store the final outcome.

        Args:
            outcome: Summary dict containing final results and score info.

        Raises:
            RuntimeError: If no active case is in progress.
            ValueError: If `outcome` is not a dict.
        """
        if self.status != "active" or self.case is None:
            raise RuntimeError("Cannot end case: no active case in progress")
        if not isinstance(outcome, dict):
            raise ValueError("outcome must be a dictionary")

        self.outcome = dict(outcome)
        self.status = "completed"

        score_info = outcome.get("score_info", {})
        if isinstance(score_info, dict) and score_info:
            self.score = max(0, int(score_info.get("score", self.score)))
            self.accuracy = max(0.0, min(100.0, float(score_info.get("accuracy", self.accuracy))))
            self.rank = str(score_info.get("rank", self.rank))

    def reset_state(self) -> None:
        """Reset all game state attributes to defaults."""
        self.case = None
        self.investigation = None
        self.interrogation = None
        self.current_suspect_id = None

        self.discovered_evidence = []
        self.discovered_clues = []
        self.interrogation_history = []

        self.hints_used = 0
        self.unnecessary_actions = 0
        self.score = 0
        self.accuracy = 0.0
        self.rank = "Detective Rookie"

        self.status = "not_started"
        self.outcome = None

    def set_current_suspect(self, suspect_id: Optional[str]) -> None:
        """Set or clear the currently focused suspect.

        Args:
            suspect_id: Suspect ID string, or None to clear selection.

        Raises:
            ValueError: If `suspect_id` is passed as a non-string object other than None.
        """
        if suspect_id is not None:
            if not isinstance(suspect_id, str) or not suspect_id.strip():
                raise ValueError("suspect_id must be a non-empty string or None")
            self.current_suspect_id = suspect_id
        else:
            self.current_suspect_id = None

    def add_discovered_evidence(self, evidence_id: str) -> bool:
        """Add a discovered evidence item ID if not already present.

        Args:
            evidence_id: Evidence identifier string.

        Returns:
            True if evidence was newly added, False if duplicate.

        Raises:
            ValueError: If `evidence_id` is empty or not a string.
        """
        if not isinstance(evidence_id, str) or not evidence_id.strip():
            raise ValueError("evidence_id must be a non-empty string")

        if evidence_id not in self.discovered_evidence:
            self.discovered_evidence.append(evidence_id)
            return True
        return False

    def add_discovered_clue(self, clue_id: str) -> bool:
        """Add a discovered clue item ID if not already present.

        Args:
            clue_id: Clue identifier string.

        Returns:
            True if clue was newly added, False if duplicate.

        Raises:
            ValueError: If `clue_id` is empty or not a string.
        """
        if not isinstance(clue_id, str) or not clue_id.strip():
            raise ValueError("clue_id must be a non-empty string")

        if clue_id not in self.discovered_clues:
            self.discovered_clues.append(clue_id)
            return True
        return False

    def record_interrogation(self, interrogation_outcome: Dict[str, Any]) -> None:
        """Record an interrogation session outcome.

        Args:
            interrogation_outcome: Dictionary outcome returned by Interrogation.end_interrogation().

        Raises:
            ValueError: If `interrogation_outcome` is not a dict.
        """
        if not isinstance(interrogation_outcome, dict):
            raise ValueError("interrogation_outcome must be a dictionary")

        self.interrogation_history.append(dict(interrogation_outcome))

    def record_hint(self) -> int:
        """Increment the count of hints used during the current case.

        Returns:
            Updated hints_used count.
        """
        self.hints_used += 1
        return self.hints_used

    def record_unnecessary_action(self) -> int:
        """Increment the count of unnecessary / redundant actions.

        Returns:
            Updated unnecessary_actions count.
        """
        self.unnecessary_actions += 1
        return self.unnecessary_actions

    def update_score(self, score: int, accuracy: float = 0.0, rank: str = "Detective Rookie") -> None:
        """Update current score, accuracy, and rank metrics safely.

        Args:
            score: Non-negative score integer.
            accuracy: Accuracy percentage float bounded [0.0, 100.0].
            rank: Rank title string.

        Raises:
            ValueError: If parameters are invalid types or out of safe range.
        """
        if not isinstance(score, int) or isinstance(score, bool):
            raise ValueError("score must be an integer")
        if score < 0:
            raise ValueError("score must be non-negative")

        if not isinstance(accuracy, (int, float)) or isinstance(accuracy, bool):
            raise ValueError("accuracy must be a number")

        if not isinstance(rank, str) or not rank.strip():
            raise ValueError("rank must be a non-empty string")

        self.score = score
        self.accuracy = max(0.0, min(100.0, float(accuracy)))
        self.rank = rank

    def update_investigation_progress(self) -> Dict[str, Any]:
        """Fetch progress snapshot from investigation if available and update metrics.

        Returns:
            Progress snapshot dict.
        """
        if self.investigation is not None and hasattr(self.investigation, "get_progress"):
            return self.investigation.get_progress()

        return {
            "status": self.status,
            "case_id": self.case.case_id if self.case else None,
            "evidence_discovered": len(self.discovered_evidence),
            "clues_discovered": len(self.discovered_clues),
            "hints_used": self.hints_used,
            "unnecessary_actions": self.unnecessary_actions,
        }

    def is_case_complete(self) -> bool:
        """Return True if the current case has been completed."""
        return self.status == "completed"

    def get_state_summary(self) -> Dict[str, Any]:
        """Return a clean dictionary snapshot of current game state."""
        return {
            "player_id": self.player.player_id if self.player else None,
            "player_name": self.player.name if self.player else None,
            "case_id": self.case.case_id if self.case else None,
            "case_title": self.case.title if self.case else None,
            "current_suspect_id": self.current_suspect_id,
            "evidence_count": len(self.discovered_evidence),
            "clues_count": len(self.discovered_clues),
            "interrogations_count": len(self.interrogation_history),
            "hints_used": self.hints_used,
            "unnecessary_actions": self.unnecessary_actions,
            "score": self.score,
            "accuracy": self.accuracy,
            "rank": self.rank,
            "status": self.status,
            "is_complete": self.is_case_complete(),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Return a complete JSON-serializable dictionary representation of the state.

        Designed for SaveManager persistence in future iterations.
        """
        return {
            "player_id": self.player.player_id if self.player else None,
            "player_name": self.player.name if self.player else None,
            "case_id": self.case.case_id if self.case else None,
            "status": self.status,
            "current_suspect_id": self.current_suspect_id,
            "discovered_evidence": list(self.discovered_evidence),
            "discovered_clues": list(self.discovered_clues),
            "interrogation_history": [dict(h) for h in self.interrogation_history],
            "hints_used": self.hints_used,
            "unnecessary_actions": self.unnecessary_actions,
            "score": self.score,
            "accuracy": self.accuracy,
            "rank": self.rank,
            "outcome": dict(self.outcome) if self.outcome else None,
        }

    def __repr__(self) -> str:
        case_id = self.case.case_id if self.case else None
        player_id = self.player.player_id if self.player else None
        return (
            f"GameState(player={player_id!r}, case={case_id!r}, "
            f"status={self.status!r}, score={self.score}, rank={self.rank!r})"
        )
