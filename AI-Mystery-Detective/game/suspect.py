"""
Suspect module for AI Mystery Detective.

Defines two classes:

- `Suspect`: represents a single suspect within a mystery case (their
  profile, alibi, recorded behavior, statements, and suspicion
  level).
- `SuspectManager`: manages a collection of `Suspect` objects and can
  load them from JSON files.

This module is intentionally independent of any UI or AI code. It
does not judge guilt, generate dialogue, or render anything -- it
only models and manages suspect data. It's designed to be used
alongside `game.case.Case`/`CaseManager` (a suspect's `suspect_id` or
`name` is expected to line up with the entries in `Case.suspects`),
but does not require importing `Case` to function.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - import only used for type hints
    from game.case import Case

# Suspicion level is kept on a fixed 0-100 scale so it can be compared
# consistently across suspects and cases.
MIN_SUSPICION_LEVEL = 0
MAX_SUSPICION_LEVEL = 100

# A generous but sane bound for human age, used purely for input
# validation (catches typos like age=-5 or age=999).
MIN_AGE = 0
MAX_AGE = 120


class Suspect:
    """Represents a single suspect in a mystery case.

    A `Suspect` is a data-holding object with light behavior for
    recording statements, behavior observations, and suspicion over
    the course of an investigation. It does not decide who's guilty
    -- that's the job of the (not-yet-implemented) `ai` module and/or
    the player.
    """

    def __init__(
        self,
        suspect_id: str,
        name: str,
        age: int,
        occupation: str,
        description: str,
        relationship_to_victim: str,
        alibi: str = "Unknown",
        behavior: Optional[List[str]] = None,
        statements: Optional[List[str]] = None,
        suspicion_level: int = 0,
    ) -> None:
        """Create a new suspect.

        Args:
            suspect_id: Unique identifier for the suspect.
            name: Suspect's display name.
            age: Suspect's age in years. Must be an integer in
                `[MIN_AGE, MAX_AGE]`.
            occupation: Suspect's job/role.
            description: Physical/character description.
            relationship_to_victim: How the suspect relates/related
                to the victim (e.g. "business partner", "spouse").
            alibi: Suspect's stated alibi. Defaults to "Unknown" if
                not yet known.
            behavior: Initial list of recorded behavior observations.
                Defaults to an empty list.
            statements: Initial list of statements made by the
                suspect. Defaults to an empty list.
            suspicion_level: Initial suspicion score. Must be an
                integer; it is clamped into
                `[MIN_SUSPICION_LEVEL, MAX_SUSPICION_LEVEL]` rather
                than raising, so slightly-out-of-range save data
                doesn't crash the game.

        Raises:
            ValueError: If a required string field is empty/not a
                string, or if `age` is not an integer within range.
        """
        for field_name, value in (
            ("suspect_id", suspect_id),
            ("name", name),
            ("occupation", occupation),
            ("description", description),
            ("relationship_to_victim", relationship_to_victim),
            ("alibi", alibi),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")

        if not isinstance(age, int) or isinstance(age, bool):
            raise ValueError("age must be an integer")
        if not (MIN_AGE <= age <= MAX_AGE):
            raise ValueError(f"age must be between {MIN_AGE} and {MAX_AGE}")

        if not isinstance(suspicion_level, int) or isinstance(suspicion_level, bool):
            raise ValueError("suspicion_level must be an integer")

        self.suspect_id: str = suspect_id
        self.name: str = name
        self.age: int = age
        self.occupation: str = occupation
        self.description: str = description
        self.relationship_to_victim: str = relationship_to_victim
        self.alibi: str = alibi

        self.behavior: List[str] = list(behavior) if behavior else []
        self.statements: List[str] = list(statements) if statements else []
        self.suspicion_level: int = self._clamp_suspicion(suspicion_level)

    # -- Internal helpers -------------------------------------------------

    @staticmethod
    def _clamp_suspicion(value: int) -> int:
        return max(MIN_SUSPICION_LEVEL, min(MAX_SUSPICION_LEVEL, value))

    # -- Statements ---------------------------------------------------------

    def add_statement(self, statement: str) -> None:
        """Record a new statement made by the suspect.

        Unlike evidence/clues elsewhere in the project, statements
        are NOT deduplicated: a suspect repeating the same claim
        (e.g. sticking to their alibi under questioning) is itself
        meaningful information.

        Args:
            statement: The statement text.

        Raises:
            ValueError: If `statement` is empty or not a string.
        """
        if not isinstance(statement, str) or not statement.strip():
            raise ValueError("statement must be a non-empty string")
        self.statements.append(statement)

    def get_statements(self) -> List[str]:
        """Return a copy of all statements recorded for this suspect."""
        return list(self.statements)

    # -- Alibi & behavior -----------------------------------------------------

    def update_alibi(self, new_alibi: str) -> None:
        """Update the suspect's stated alibi.

        Args:
            new_alibi: The new alibi text.

        Raises:
            ValueError: If `new_alibi` is empty or not a string.
        """
        if not isinstance(new_alibi, str) or not new_alibi.strip():
            raise ValueError("new_alibi must be a non-empty string")
        self.alibi = new_alibi

    def record_behavior(self, behavior_note: str) -> None:
        """Record an observed behavior for this suspect.

        Like statements, behavior notes are not deduplicated -- a
        suspect being observed to act nervously multiple times is
        meaningful.

        Args:
            behavior_note: Description of the observed behavior.

        Raises:
            ValueError: If `behavior_note` is empty or not a string.
        """
        if not isinstance(behavior_note, str) or not behavior_note.strip():
            raise ValueError("behavior_note must be a non-empty string")
        self.behavior.append(behavior_note)

    # -- Suspicion level ----------------------------------------------------

    def update_suspicion_level(self, delta: int) -> int:
        """Adjust the suspicion level by `delta`.

        The result is clamped to `[MIN_SUSPICION_LEVEL,
        MAX_SUSPICION_LEVEL]`.

        Args:
            delta: Amount to add (may be negative to decrease
                suspicion).

        Returns:
            The suspect's new suspicion level.

        Raises:
            ValueError: If `delta` is not an integer.
        """
        if not isinstance(delta, int) or isinstance(delta, bool):
            raise ValueError("delta must be an integer")
        self.suspicion_level = self._clamp_suspicion(self.suspicion_level + delta)
        return self.suspicion_level

    def reset_suspicion_level(self) -> None:
        """Reset the suspicion level back to 0."""
        self.suspicion_level = MIN_SUSPICION_LEVEL

    # -- Info retrieval ---------------------------------------------------

    def get_info(self) -> Dict[str, Any]:
        """Return a dictionary summarizing the suspect's full profile.

        Returns:
            A dictionary with all suspect fields, including copies of
            the `behavior` and `statements` lists (so callers can't
            mutate internal state by reference).
        """
        return {
            "suspect_id": self.suspect_id,
            "name": self.name,
            "age": self.age,
            "occupation": self.occupation,
            "description": self.description,
            "relationship_to_victim": self.relationship_to_victim,
            "alibi": self.alibi,
            "behavior": list(self.behavior),
            "statements": list(self.statements),
            "suspicion_level": self.suspicion_level,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Return the suspect's data as a plain dictionary (for saving)."""
        return self.get_info()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Suspect":
        """Build a `Suspect` from a plain dictionary (e.g. parsed JSON).

        Args:
            data: Dictionary containing at least the required fields
                (suspect_id, name, age, occupation, description,
                relationship_to_victim). Optional fields (alibi,
                behavior, statements, suspicion_level) fall back to
                their `Suspect.__init__` defaults if missing.

        Returns:
            A new `Suspect` instance.

        Raises:
            KeyError: If a required field is missing from `data`.
            ValueError: If a field has an invalid value.
        """
        required = (
            "suspect_id",
            "name",
            "age",
            "occupation",
            "description",
            "relationship_to_victim",
        )
        missing = [field for field in required if field not in data]
        if missing:
            raise KeyError(f"Missing required suspect field(s): {missing}")

        return cls(
            suspect_id=data["suspect_id"],
            name=data["name"],
            age=data["age"],
            occupation=data["occupation"],
            description=data["description"],
            relationship_to_victim=data["relationship_to_victim"],
            alibi=data.get("alibi", "Unknown"),
            behavior=data.get("behavior", []),
            statements=data.get("statements", []),
            suspicion_level=data.get("suspicion_level", 0),
        )

    def __repr__(self) -> str:
        return (
            f"Suspect(suspect_id={self.suspect_id!r}, name={self.name!r}, "
            f"suspicion_level={self.suspicion_level})"
        )


class SuspectManager:
    """Manages a collection of `Suspect` objects.

    Suspects can be added directly (`add_case`-style, via
    `add_suspect`) or loaded from JSON files. Each JSON file may
    contain either a single suspect object or a list of suspect
    objects, which makes it easy to keep one file per case.
    """

    def __init__(self, suspects_dir: Optional[str] = None) -> None:
        """Create a suspect manager.

        Args:
            suspects_dir: Optional default directory to load suspect
                JSON files from when `load_all_suspects()` is called
                without an explicit directory. Unlike `CaseManager`,
                no directory is assumed by default, since suspect
                data may be organized per-case rather than in one
                fixed folder.
        """
        self.suspects_dir: Optional[Path] = Path(suspects_dir) if suspects_dir else None
        self._suspects: Dict[str, Suspect] = {}
        self._load_errors: List[str] = []

    def add_suspect(self, suspect: Suspect) -> None:
        """Register a `Suspect` object directly with the manager.

        Args:
            suspect: The `Suspect` instance to add.

        Raises:
            TypeError: If `suspect` is not a `Suspect` instance.
            ValueError: If a suspect with the same `suspect_id` is
                already registered.
        """
        if not isinstance(suspect, Suspect):
            raise TypeError("suspect must be a Suspect instance")
        if suspect.suspect_id in self._suspects:
            raise ValueError(
                f"Suspect with id '{suspect.suspect_id}' already exists"
            )
        self._suspects[suspect.suspect_id] = suspect

    def load_suspect_from_file(self, file_path: Union[str, Path]) -> List[Suspect]:
        """Load one or more suspects from a single JSON file.

        The file may contain either a JSON object (one suspect) or a
        JSON array of objects (multiple suspects). Invalid or
        unreadable files do not raise -- errors are recorded (see
        `get_load_errors`) and an empty list is returned, so a single
        bad file doesn't stop the rest of a directory from loading.

        Args:
            file_path: Path to a `.json` suspect file.

        Returns:
            List of successfully loaded `Suspect` objects from this
            file (empty if loading failed entirely).
        """
        file_path = Path(file_path)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            self._load_errors.append(f"{file_path}: file not found")
            return []
        except json.JSONDecodeError as exc:
            self._load_errors.append(f"{file_path}: invalid JSON ({exc})")
            return []

        records = data if isinstance(data, list) else [data]

        loaded: List[Suspect] = []
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                self._load_errors.append(
                    f"{file_path}[{index}]: expected an object, got {type(record).__name__}"
                )
                continue
            try:
                suspect = Suspect.from_dict(record)
            except (KeyError, ValueError, TypeError) as exc:
                self._load_errors.append(f"{file_path}[{index}]: invalid suspect data ({exc})")
                continue
            try:
                self.add_suspect(suspect)
            except ValueError as exc:
                self._load_errors.append(f"{file_path}[{index}]: {exc}")
                continue
            loaded.append(suspect)

        return loaded

    def load_all_suspects(self, directory: Optional[Union[str, Path]] = None) -> List[Suspect]:
        """Load every `.json` file in a directory as suspect data.

        Args:
            directory: Directory to scan. Falls back to
                `self.suspects_dir` if omitted.

        Returns:
            List of successfully loaded `Suspect` objects (newly
            loaded in this call).

        Raises:
            ValueError: If no directory is given and no default
                `suspects_dir` was set.
        """
        target_dir = Path(directory) if directory is not None else self.suspects_dir
        if target_dir is None:
            raise ValueError(
                "No directory given and no default suspects_dir was set"
            )

        if not target_dir.exists():
            self._load_errors.append(f"{target_dir}: suspects directory does not exist")
            return []

        loaded: List[Suspect] = []
        for file_path in sorted(target_dir.glob("*.json")):
            loaded.extend(self.load_suspect_from_file(file_path))

        return loaded

    def get_suspect(self, suspect_id: str) -> Optional[Suspect]:
        """Retrieve a suspect by id, or None if not found."""
        return self._suspects.get(suspect_id)

    def get_all_suspects(self) -> List[Suspect]:
        """Return all currently registered suspects."""
        return list(self._suspects.values())

    def get_suspects_by_names(self, names: List[str]) -> List[Suspect]:
        """Return registered suspects whose `name` is in `names`.

        Useful for cross-referencing with `Case.suspects`, which
        stores suspect names/ids as plain strings.
        """
        name_set = set(names)
        return [s for s in self._suspects.values() if s.name in name_set]

    def get_suspects_for_case(self, case: "Case") -> List[Suspect]:
        """Return the registered suspects referenced by a `Case`.

        This is a convenience method for keeping `SuspectManager` in
        sync with `game.case.Case`/`CaseManager`: it looks up
        `case.suspects` (a list of names/ids) against the suspects
        registered here. It works with any object exposing a
        `.suspects` list of strings, so it doesn't require importing
        `Case` at runtime.

        Args:
            case: A `Case` instance (or any object with a `.suspects`
                list of strings).

        Returns:
            The subset of registered suspects referenced by the case.
        """
        return self.get_suspects_by_names(list(case.suspects))

    def get_load_errors(self) -> List[str]:
        """Return a list of human-readable errors from failed loads."""
        return list(self._load_errors)

    def __len__(self) -> int:
        return len(self._suspects)

    def __repr__(self) -> str:
        return f"SuspectManager(loaded={len(self)})"
