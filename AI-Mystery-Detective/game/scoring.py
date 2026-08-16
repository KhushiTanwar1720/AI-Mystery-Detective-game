"""
Scoring and Ranking module for AI Mystery Detective.

Defines:
- `ScoringConfig`: Dataclass holding all configurable point values,
  penalties, multipliers, and rank threshold definitions.
- `ScoreManager`: OOP class managing case scoring, accuracy calculation,
  ranking tier determination, and score summaries.

This module is intentionally independent of any UI logic.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ScoringConfig:
    """Configurable parameters for scoring rules and rank thresholds."""

    correct_suspect_points: int = 500
    wrong_suspect_penalty: int = 200
    evidence_base_points: int = 50
    clue_base_points: int = 30
    contradiction_points: int = 75
    unnecessary_action_penalty: int = 10
    hint_penalty: int = 25
    time_bonus_max: int = 100
    time_bonus_action_threshold: int = 20
    time_bonus_cutoff: int = 60

    importance_weights: Dict[str, float] = field(
        default_factory=lambda: {
            "low": 1.0,
            "medium": 2.0,
            "high": 3.0,
            "critical": 5.0,
        }
    )

    difficulty_multipliers: Dict[str, float] = field(
        default_factory=lambda: {
            "easy": 1.0,
            "medium": 1.25,
            "hard": 1.5,
        }
    )

    # Thresholds sorted ascending by minimum score requirement
    rank_thresholds: List[Tuple[int, str]] = field(
        default_factory=lambda: [
            (0, "Detective Rookie"),
            (300, "Investigator"),
            (600, "Senior Detective"),
            (900, "Master Detective"),
        ]
    )

    def validate(self) -> None:
        """Validate config values to ensure non-negative logic where required."""
        if self.correct_suspect_points < 0:
            raise ValueError("correct_suspect_points must be non-negative")
        if self.wrong_suspect_penalty < 0:
            raise ValueError("wrong_suspect_penalty must be non-negative")
        if self.evidence_base_points < 0:
            raise ValueError("evidence_base_points must be non-negative")
        if self.clue_base_points < 0:
            raise ValueError("clue_base_points must be non-negative")
        if self.contradiction_points < 0:
            raise ValueError("contradiction_points must be non-negative")
        if self.unnecessary_action_penalty < 0:
            raise ValueError("unnecessary_action_penalty must be non-negative")
        if self.hint_penalty < 0:
            raise ValueError("hint_penalty must be non-negative")
        if self.time_bonus_max < 0:
            raise ValueError("time_bonus_max must be non-negative")


class ScoreManager:
    """Manages case score computation, accuracy, and player rank assignment."""

    def __init__(self, config: Optional[ScoringConfig] = None) -> None:
        """Initialize ScoreManager with an optional custom `ScoringConfig`.

        Args:
            config: Configuration object containing scoring multipliers and
                thresholds. If None, default `ScoringConfig` is used.
        """
        self.config: ScoringConfig = config or ScoringConfig()
        self.config.validate()
        self._score: int = 0
        self._breakdown: Dict[str, int] = {}
        self._accuracy: float = 0.0

    @property
    def current_score(self) -> int:
        """Return current calculated score."""
        return self._score

    @property
    def current_accuracy(self) -> float:
        """Return current calculated accuracy (0.0 to 100.0)."""
        return self._accuracy

    def add_points(self, points: int) -> int:
        """Add points to the current running score safely.

        Args:
            points: Number of points to add. Must be an integer.

        Returns:
            Updated total score.

        Raises:
            ValueError: If `points` is not an integer or is negative.
        """
        if not isinstance(points, int) or isinstance(points, bool):
            raise ValueError("points must be an integer")
        if points < 0:
            raise ValueError("points to add must be non-negative")

        self._score += points
        return self._score

    def deduct_points(self, points: int) -> int:
        """Deduct points from the current running score, floored at 0.

        Args:
            points: Number of points to deduct. Must be an integer.

        Returns:
            Updated total score.

        Raises:
            ValueError: If `points` is not an integer or is negative.
        """
        if not isinstance(points, int) or isinstance(points, bool):
            raise ValueError("points must be an integer")
        if points < 0:
            raise ValueError("points to deduct must be non-negative")

        self._score = max(0, self._score - points)
        return self._score

    def reset_score(self) -> None:
        """Reset current score, breakdown, and accuracy."""
        self._score = 0
        self._breakdown = {}
        self._accuracy = 0.0

    def calculate_accuracy(
        self,
        solved: bool,
        discovered_evidence_count: int = 0,
        total_evidence_count: int = 0,
        discovered_clues_count: int = 0,
        total_clues_count: int = 0,
        unnecessary_actions: int = 0,
        hints_used: int = 0,
    ) -> float:
        """Calculate overall accuracy percentage bounded between 0.0 and 100.0.

        Formula considers:
        - Accusation correctness (50% weight)
        - Evidence & clue discovery completion (40% weight)
        - Efficiency penalty for unnecessary actions and hints (up to -30% penalty)

        Args:
            solved: Whether the correct suspect was accused.
            discovered_evidence_count: Count of evidence found.
            total_evidence_count: Total available evidence.
            discovered_clues_count: Count of clues found.
            total_clues_count: Total available clues.
            unnecessary_actions: Count of redundant or invalid actions.
            hints_used: Count of hints requested.

        Returns:
            Accuracy value as a float bounded within [0.0, 100.0].
        """
        # Input validation / sanity checks
        discovered_evidence_count = max(0, int(discovered_evidence_count or 0))
        total_evidence_count = max(0, int(total_evidence_count or 0))
        discovered_clues_count = max(0, int(discovered_clues_count or 0))
        total_clues_count = max(0, int(total_clues_count or 0))
        unnecessary_actions = max(0, int(unnecessary_actions or 0))
        hints_used = max(0, int(hints_used or 0))

        accusation_score = 50.0 if solved else 0.0

        total_items = total_evidence_count + total_clues_count
        discovered_items = min(total_items, discovered_evidence_count + discovered_clues_count)

        if total_items > 0:
            discovery_score = (discovered_items / total_items) * 50.0
        else:
            discovery_score = 50.0 if solved else 0.0


        base_accuracy = accusation_score + discovery_score

        # Deductions
        penalty = (unnecessary_actions * 2.0) + (hints_used * 5.0)
        final_accuracy = max(0.0, min(100.0, base_accuracy - penalty))

        self._accuracy = round(final_accuracy, 2)
        return self._accuracy

    def calculate_score(
        self,
        solved: bool,
        evidence_list: Optional[List[Dict[str, Any]]] = None,
        clues_list: Optional[List[Dict[str, Any]]] = None,
        contradictions_found: int = 0,
        unnecessary_actions: int = 0,
        action_count: int = 0,
        hints_used: int = 0,
        difficulty: str = "easy",
        total_evidence_count: int = 0,
        total_clues_count: int = 0,
    ) -> int:
        """Calculate and store the total case score based on performance metrics.

        Args:
            solved: True if correct suspect was accused.
            evidence_list: Discovered evidence dict items (with `importance`).
            clues_list: Discovered clue dict items (with `importance`).
            contradictions_found: Number of interrogation contradictions uncovered.
            unnecessary_actions: Redundant visits or invalid actions.
            action_count: Total action/investigation time metric.
            hints_used: Number of hints asked.
            difficulty: Case difficulty tier ("easy", "medium", "hard").
            total_evidence_count: Total evidence count for accuracy calc.
            total_clues_count: Total clue count for accuracy calc.

        Returns:
            The final calculated score integer (>= 0).
        """
        self.reset_score()

        evidence_list = evidence_list or []
        clues_list = clues_list or []

        # 1. Suspect Accusation Points
        suspect_pts = (
            self.config.correct_suspect_points
            if solved
            else -self.config.wrong_suspect_penalty
        )

        # 2. Evidence Points
        evidence_pts = 0
        for item in evidence_list:
            imp = str(item.get("importance", "low")).lower()
            weight = self.config.importance_weights.get(imp, 1.0)
            evidence_pts += int(self.config.evidence_base_points * weight)

        # 3. Clue Points
        clue_pts = 0
        for item in clues_list:
            imp = str(item.get("importance", "low")).lower()
            weight = self.config.importance_weights.get(imp, 1.0)
            clue_pts += int(self.config.clue_base_points * weight)

        # 4. Interrogation Contradictions
        safe_contradictions = max(0, int(contradictions_found or 0))
        contradiction_pts = safe_contradictions * self.config.contradiction_points

        # 5. Time / Efficiency Bonus
        safe_action_count = max(0, int(action_count or 0))
        if safe_action_count <= self.config.time_bonus_action_threshold:
            time_bonus = self.config.time_bonus_max
        elif safe_action_count >= self.config.time_bonus_cutoff:
            time_bonus = 0
        else:
            span = self.config.time_bonus_cutoff - self.config.time_bonus_action_threshold
            elapsed = safe_action_count - self.config.time_bonus_action_threshold
            ratio = 1.0 - (elapsed / span)
            time_bonus = int(self.config.time_bonus_max * ratio)

        # 6. Unnecessary Actions Penalty
        safe_unnecessary = max(0, int(unnecessary_actions or 0))
        unnecessary_penalty = safe_unnecessary * self.config.unnecessary_action_penalty

        # 7. Hints Used Penalty
        safe_hints = max(0, int(hints_used or 0))
        hint_penalty = safe_hints * self.config.hint_penalty

        # Raw Total
        raw_total = (
            suspect_pts
            + evidence_pts
            + clue_pts
            + contradiction_pts
            + time_bonus
            - unnecessary_penalty
            - hint_penalty
        )

        # 8. Difficulty Multiplier
        diff_key = str(difficulty or "easy").lower()
        multiplier = self.config.difficulty_multipliers.get(diff_key, 1.0)

        final_score = max(0, int(round(raw_total * multiplier)))

        self._score = final_score
        self._breakdown = {
            "suspect_points": suspect_pts,
            "evidence_points": evidence_pts,
            "clue_points": clue_pts,
            "contradiction_points": contradiction_pts,
            "time_bonus": time_bonus,
            "unnecessary_penalty": unnecessary_penalty,
            "hint_penalty": hint_penalty,
            "raw_total": raw_total,
            "difficulty_multiplier": multiplier,
            "final_score": final_score,
        }

        # Calculate accuracy as well
        self.calculate_accuracy(
            solved=solved,
            discovered_evidence_count=len(evidence_list),
            total_evidence_count=total_evidence_count or len(evidence_list),
            discovered_clues_count=len(clues_list),
            total_clues_count=total_clues_count or len(clues_list),
            unnecessary_actions=safe_unnecessary,
            hints_used=safe_hints,
        )

        return self._score

    def get_rank(self, score: Optional[int] = None) -> str:
        """Determine player rank tier based on current or provided score.

        Args:
            score: Optional score integer to evaluate rank for. If None,
                uses `self.current_score`.

        Returns:
            Rank string (e.g. "Senior Detective").
        """
        target_score = self._score if score is None else max(0, int(score))

        assigned_rank = self.config.rank_thresholds[0][1]
        for min_score, rank_name in sorted(self.config.rank_thresholds, key=lambda x: x[0]):
            if target_score >= min_score:
                assigned_rank = rank_name

        return assigned_rank

    def get_score_summary(self) -> Dict[str, Any]:
        """Return comprehensive score, breakdown, accuracy, and rank summary."""
        return {
            "score": self._score,
            "accuracy": self._accuracy,
            "rank": self.get_rank(),
            "breakdown": dict(self._breakdown),
        }
