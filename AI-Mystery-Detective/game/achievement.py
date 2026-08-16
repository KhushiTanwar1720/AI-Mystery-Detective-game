"""
Achievement module for AI Mystery Detective.

Defines two classes:

- `Achievement`: represents a single unlockable achievement (its id,
  display name/description, the requirement that must be satisfied
  to unlock it, and its unlock state/timestamp).
- `AchievementManager`: registers, tracks, checks, and unlocks a
  collection of `Achievement` objects.

This module is intentionally independent of the UI, and does not
duplicate any logic that already lives in `Player`, `GameState`,
`Investigation`, or `ScoreManager`. Instead, `AchievementManager`
evaluates achievement requirements against a plain statistics
dictionary that a caller (typically `GameController`) builds by
reading those other modules -- `AchievementManager` never reaches
into them directly.

Requirements are expressed declaratively, as a list of simple
condition dictionaries (`{"stat": ..., "operator": ..., "value": ...}`),
so new achievements can be added or reconfigured without changing any
manager code.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Requirement conditions are combined with logical AND: an achievement
# unlocks only once every condition in its `requirement` list matches
# the current statistics.
VALID_OPERATORS = (">=", "<=", ">", "<", "==", "!=")


class Achievement:
    """Represents a single unlockable achievement.

    Attributes:
        achievement_id: Unique identifier for this achievement.
        name: Short display name (e.g. "First Case").
        description: Human-readable description of how to earn it.
        requirement: List of condition dictionaries, each with a
            `stat` key (name of a statistic), an `operator` key (one
            of `VALID_OPERATORS`), and a `value` key. All conditions
            must hold for the achievement to unlock.
        unlocked: Whether the achievement has been unlocked.
        unlocked_at: UTC ISO-8601 timestamp of when the achievement
            was unlocked, or None if it hasn't been.
    """

    def __init__(
        self,
        achievement_id: str,
        name: str,
        description: str,
        requirement: List[Dict[str, Any]],
        unlocked: bool = False,
        unlocked_at: Optional[str] = None,
    ) -> None:
        """Create a new achievement definition.

        Args:
            achievement_id: Unique identifier. Must be a non-empty
                string.
            name: Display name. Must be a non-empty string.
            description: Description of the achievement. Must be a
                non-empty string.
            requirement: List of condition dictionaries (see class
                docstring). May be empty (an achievement with no
                conditions is trivially satisfiable).
            unlocked: Initial unlock state. Defaults to False.
            unlocked_at: Initial unlock timestamp. Should only be set
                together with `unlocked=True`.

        Raises:
            ValueError: If a required string field is empty/not a
                string, `requirement` is not a list of well-formed
                condition dicts, or `unlocked` is not a bool.
        """
        for field_name, value in (
            ("achievement_id", achievement_id),
            ("name", name),
            ("description", description),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")

        if not isinstance(unlocked, bool):
            raise ValueError("unlocked must be a boolean")

        self.achievement_id: str = achievement_id
        self.name: str = name
        self.description: str = description
        self.requirement: List[Dict[str, Any]] = self._validate_requirement(requirement)
        self.unlocked: bool = unlocked
        self.unlocked_at: Optional[str] = unlocked_at if unlocked else None

    @staticmethod
    def _validate_requirement(requirement: Any) -> List[Dict[str, Any]]:
        """Validate and normalize a requirement condition list.

        Raises:
            ValueError: If `requirement` isn't a list of dicts each
                containing a non-empty `stat` string and a supported
                `operator`.
        """
        if requirement is None:
            return []
        if not isinstance(requirement, list):
            raise ValueError("requirement must be a list of condition dictionaries")

        normalized: List[Dict[str, Any]] = []
        for condition in requirement:
            if not isinstance(condition, dict):
                raise ValueError("each requirement condition must be a dictionary")
            stat = condition.get("stat")
            operator = condition.get("operator", "==")
            if not isinstance(stat, str) or not stat.strip():
                raise ValueError("each requirement condition needs a non-empty 'stat'")
            if operator not in VALID_OPERATORS:
                raise ValueError(
                    f"operator must be one of {VALID_OPERATORS}, got {operator!r}"
                )
            normalized.append(
                {"stat": stat, "operator": operator, "value": condition.get("value")}
            )
        return normalized

    # -- Unlocking ------------------------------------------------------------

    def unlock(self) -> bool:
        """Mark this achievement as unlocked, recording a timestamp.

        Safe/idempotent: calling this on an already-unlocked
        achievement does nothing and leaves the original
        `unlocked_at` timestamp untouched.

        Returns:
            True if the achievement was newly unlocked by this call,
            False if it was already unlocked.
        """
        if self.unlocked:
            return False

        self.unlocked = True
        self.unlocked_at = datetime.now(timezone.utc).isoformat()
        return True

    def is_unlocked(self) -> bool:
        """Return whether this achievement has been unlocked."""
        return self.unlocked

    def reset(self) -> None:
        """Reset this achievement back to its locked state."""
        self.unlocked = False
        self.unlocked_at = None

    # -- Serialization ----------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return the full achievement data as a dictionary (for saving)."""
        return {
            "achievement_id": self.achievement_id,
            "name": self.name,
            "description": self.description,
            "requirement": [dict(condition) for condition in self.requirement],
            "unlocked": self.unlocked,
            "unlocked_at": self.unlocked_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Achievement":
        """Build an `Achievement` from a plain dictionary (e.g. parsed JSON).

        Args:
            data: Dictionary containing at least the required fields
                (achievement_id, name, description). Optional fields
                (requirement, unlocked, unlocked_at) fall back to
                `Achievement.__init__` defaults if missing.

        Returns:
            A new `Achievement` instance.

        Raises:
            KeyError: If a required field is missing from `data`.
            ValueError: If a field has an invalid value.
        """
        required = ("achievement_id", "name", "description")
        missing = [field for field in required if field not in data]
        if missing:
            raise KeyError(f"Missing required achievement field(s): {missing}")

        return cls(
            achievement_id=data["achievement_id"],
            name=data["name"],
            description=data["description"],
            requirement=data.get("requirement", []),
            unlocked=bool(data.get("unlocked", False)),
            unlocked_at=data.get("unlocked_at"),
        )

    def __repr__(self) -> str:
        return (
            f"Achievement(achievement_id={self.achievement_id!r}, "
            f"unlocked={self.unlocked}, unlocked_at={self.unlocked_at!r})"
        )


def _default_achievement_specs() -> List[Dict[str, Any]]:
    """Return the plain-dict specs for the game's default achievement set.

    Kept as a module-level function (rather than inline in
    `create_default_achievements`) purely so tests/tools can inspect
    the raw specs without constructing `Achievement` objects.
    """
    return [
        {
            "achievement_id": "first_case",
            "name": "First Case",
            "description": "Complete your first case.",
            "requirement": [
                {"stat": "solved", "operator": "==", "value": True},
                {"stat": "cases_solved", "operator": ">=", "value": 1},
            ],
        },
        {
            "achievement_id": "evidence_hunter",
            "name": "Evidence Hunter",
            "description": "Discover all available evidence in a case.",
            "requirement": [
                {"stat": "all_evidence_discovered", "operator": "==", "value": True}
            ],
        },
        {
            "achievement_id": "clue_collector",
            "name": "Clue Collector",
            "description": "Discover all available clues in a case.",
            "requirement": [
                {"stat": "all_clues_discovered", "operator": "==", "value": True}
            ],
        },
        {
            "achievement_id": "master_investigator",
            "name": "Master Investigator",
            "description": "Complete a case with high investigation accuracy.",
            "requirement": [
                {"stat": "solved", "operator": "==", "value": True},
                {"stat": "accuracy", "operator": ">=", "value": 90.0},
            ],
        },
        {
            "achievement_id": "no_hint_detective",
            "name": "No-Hint Detective",
            "description": "Successfully complete a case without using any hints.",
            "requirement": [
                {"stat": "solved", "operator": "==", "value": True},
                {"stat": "no_hints_used", "operator": "==", "value": True},
            ],
        },
        {
            "achievement_id": "speed_detective",
            "name": "Speed Detective",
            "description": "Solve a case within the configured target time.",
            "requirement": [
                {"stat": "solved", "operator": "==", "value": True},
                {"stat": "within_target_time", "operator": "==", "value": True},
            ],
        },
        {
            "achievement_id": "perfect_investigation",
            "name": "Perfect Investigation",
            "description": (
                "Discover all relevant evidence and clues and correctly "
                "identify the suspect."
            ),
            "requirement": [
                {"stat": "all_evidence_discovered", "operator": "==", "value": True},
                {"stat": "all_clues_discovered", "operator": "==", "value": True},
                {"stat": "solved", "operator": "==", "value": True},
            ],
        },
        {
            "achievement_id": "master_detective",
            "name": "Master Detective",
            "description": "Reach the Master Detective rank.",
            "requirement": [
                {"stat": "rank", "operator": "==", "value": "Master Detective"}
            ],
        },
    ]


def create_default_achievements() -> List[Achievement]:
    """Build fresh `Achievement` instances for the default achievement set.

    Returns a brand-new list of unlocked=False `Achievement` objects
    every call, so callers (e.g. `AchievementManager()`) never share
    mutable state.
    """
    return [Achievement.from_dict(spec) for spec in _default_achievement_specs()]


class AchievementManager:
    """Registers, tracks, checks, and unlocks a collection of achievements.

    `AchievementManager` owns only `Achievement` objects and pure
    comparison logic -- it has no knowledge of `Player`, `GameState`,
    `Investigation`, or `ScoreManager` internals. Callers are
    responsible for building a flat statistics dictionary from those
    modules (see `game.game_controller.GameController` for the
    reference implementation) and passing it to `check_achievements`.
    """

    def __init__(self, achievements: Optional[List[Achievement]] = None) -> None:
        """Initialize the manager, optionally with a starting achievement set.

        Args:
            achievements: Initial achievements to register. If None,
                the default achievement set (see
                `create_default_achievements`) is used.

        Raises:
            ValueError: If `achievements` contains a duplicate
                `achievement_id` or a non-`Achievement` item.
        """
        self._achievements: Dict[str, Achievement] = {}

        for achievement in (
            achievements if achievements is not None else create_default_achievements()
        ):
            self.add_achievement(achievement)

    # -- Registration -----------------------------------------------------

    def add_achievement(self, achievement: Achievement) -> None:
        """Register a new achievement.

        Args:
            achievement: `Achievement` instance to register.

        Raises:
            ValueError: If `achievement` isn't an `Achievement`
                instance, or its `achievement_id` is already
                registered.
        """
        if not isinstance(achievement, Achievement):
            raise ValueError("achievement must be an Achievement instance")
        if achievement.achievement_id in self._achievements:
            raise ValueError(
                f"Achievement '{achievement.achievement_id}' is already registered"
            )
        self._achievements[achievement.achievement_id] = achievement

    def get_achievement(self, achievement_id: str) -> Optional[Achievement]:
        """Return the achievement with `achievement_id`, or None if unknown."""
        return self._achievements.get(achievement_id)

    def get_all_achievements(self) -> List[Achievement]:
        """Return every registered achievement, in registration order."""
        return list(self._achievements.values())

    # -- Checking / unlocking -----------------------------------------------

    def check_requirement(
        self, achievement: Achievement, stats: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Return True if `achievement`'s requirement is met by `stats`.

        Missing or incomplete statistics are handled gracefully: a
        condition whose `stat` key isn't present in `stats` simply
        fails to match (rather than raising), so an achievement with
        an unmet-but-not-yet-computed statistic is just reported as
        not (yet) satisfied.

        Args:
            achievement: The achievement to evaluate.
            stats: Flat dictionary of current statistics (e.g.
                `{"cases_solved": 1, "solved": True, ...}`). Treated
                as empty if None.

        Returns:
            True if every condition in `achievement.requirement`
            matches `stats`; False otherwise (including when
            `achievement.requirement` is malformed in a way that
            can't be evaluated).
        """
        stats = stats or {}

        for condition in achievement.requirement:
            stat_name = condition["stat"]
            operator = condition["operator"]
            expected = condition["value"]

            if stat_name not in stats:
                return False

            actual = stats[stat_name]
            try:
                if operator == ">=":
                    matched = actual >= expected
                elif operator == "<=":
                    matched = actual <= expected
                elif operator == ">":
                    matched = actual > expected
                elif operator == "<":
                    matched = actual < expected
                elif operator == "!=":
                    matched = actual != expected
                else:  # "=="
                    matched = actual == expected
            except TypeError:
                # Incomparable types (e.g. a stat that's None where a
                # number was expected) -- treat as not matching rather
                # than propagating an error from a statistics gap.
                matched = False

            if not matched:
                return False

        return True

    def unlock_achievement(self, achievement_id: str) -> bool:
        """Unlock a specific achievement by id, if not already unlocked.

        Args:
            achievement_id: Id of the achievement to unlock.

        Returns:
            True if the achievement was newly unlocked, False if it
            was already unlocked or `achievement_id` is unknown.
        """
        achievement = self._achievements.get(achievement_id)
        if achievement is None:
            return False
        return achievement.unlock()

    def check_achievements(self, stats: Optional[Dict[str, Any]] = None) -> List[Achievement]:
        """Check every locked achievement against `stats` and unlock matches.

        Safe to call repeatedly (e.g. after every game event) --
        already-unlocked achievements are skipped, so nothing is ever
        unlocked twice or gets its `unlocked_at` timestamp overwritten.

        Args:
            stats: Flat dictionary of current statistics.

        Returns:
            The list of `Achievement` objects newly unlocked by this
            call (empty if none).
        """
        newly_unlocked: List[Achievement] = []
        for achievement in self._achievements.values():
            if achievement.unlocked:
                continue
            if self.check_requirement(achievement, stats):
                if achievement.unlock():
                    newly_unlocked.append(achievement)
        return newly_unlocked

    # -- Queries ------------------------------------------------------------

    def get_unlocked_achievements(self) -> List[Achievement]:
        """Return every currently unlocked achievement."""
        return [a for a in self._achievements.values() if a.unlocked]

    def get_locked_achievements(self) -> List[Achievement]:
        """Return every currently locked achievement."""
        return [a for a in self._achievements.values() if not a.unlocked]

    def get_progress(self) -> Dict[str, Any]:
        """Return a snapshot summary of overall achievement progress.

        Returns:
            A dictionary with unlocked/total counts, a completion
            percentage, and the ids of unlocked achievements.
        """
        total = len(self._achievements)
        unlocked = self.get_unlocked_achievements()
        unlocked_count = len(unlocked)
        percent = round((unlocked_count / total) * 100, 1) if total > 0 else 0.0

        return {
            "unlocked_count": unlocked_count,
            "total_count": total,
            "completion_percent": percent,
            "unlocked_ids": [a.achievement_id for a in unlocked],
        }

    # -- Resetting ------------------------------------------------------------

    def reset(self) -> None:
        """Reset every registered achievement back to its locked state."""
        for achievement in self._achievements.values():
            achievement.reset()

    # -- Serialization ----------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        """Return all achievement state as a JSON-serializable dictionary.

        Designed for `SaveManager` persistence: captures each
        achievement's full definition plus its current unlock
        state/timestamp, so a reload can restore both without needing
        the default achievement set to be rebuilt first.
        """
        return {
            "achievements": [a.to_dict() for a in self._achievements.values()]
        }

    @classmethod
    def from_dict(cls, data: Optional[Dict[str, Any]]) -> "AchievementManager":
        """Build an `AchievementManager` from a plain dictionary.

        Args:
            data: Dictionary previously produced by `to_dict()`
                (i.e. with an `"achievements"` list). If None, empty,
                or malformed, the default achievement set is used
                instead -- this keeps old saves (created before the
                achievement system existed) loadable without any
                achievement data at all.

        Returns:
            A new `AchievementManager` instance.
        """
        if not isinstance(data, dict) or not data.get("achievements"):
            return cls()

        manager = cls(achievements=[])
        for item in data["achievements"]:
            if not isinstance(item, dict):
                continue
            try:
                manager.add_achievement(Achievement.from_dict(item))
            except (KeyError, ValueError):
                continue

        # If nothing valid was found in an otherwise-present but
        # corrupt "achievements" list, fall back to the default set
        # rather than handing back a manager with zero achievements.
        if not manager._achievements:
            return cls()

        return manager

    def __repr__(self) -> str:
        return (
            f"AchievementManager(total={len(self._achievements)}, "
            f"unlocked={len(self.get_unlocked_achievements())})"
        )
