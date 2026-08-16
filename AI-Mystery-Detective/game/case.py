"""
Case module for AI Mystery Detective.

Defines two classes:

- `Case`: represents a single mystery case (its metadata, suspects,
  evidence, clues, and solve status).
- `CaseManager`: loads `Case` objects from JSON files in the `cases/`
  directory and manages the collection.

This module is intentionally independent of any UI or AI code. It
does not analyze evidence, generate hints, or render anything -- it
only models and manages case data.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# Valid lifecycle states for a Case.
VALID_STATUSES = ("not_started", "in_progress", "solved", "failed")

# Recognized difficulty levels. Kept loose (any non-empty string is
# technically accepted by Case itself) but this list is used by
# CaseManager for basic sanity checks when loading from JSON.
VALID_DIFFICULTIES = ("easy", "medium", "hard")


class Case:
    """Represents a single mystery case.

    A `Case` is a data-holding object with light behavior for
    managing its own suspects, evidence, clues, and status. It does
    not know how to render itself or reason about who's guilty --
    that's the job of future `ui` and `ai` modules.
    """

    def __init__(
        self,
        case_id: str,
        title: str,
        description: str,
        location: str,
        crime_type: str,
        difficulty: str,
        correct_suspect: str,
        suspects: Optional[List[str]] = None,
        evidence: Optional[List[str]] = None,
        clues: Optional[List[str]] = None,
        locations: Optional[List[str]] = None,
        status: str = "not_started",
    ) -> None:
        """Create a new case.

        Args:
            case_id: Unique identifier for the case.
            title: Short human-readable case title.
            description: Longer narrative description of the case.
            location: Where the crime took place.
            crime_type: Category of crime (e.g. "theft", "murder").
            difficulty: Difficulty level (e.g. "easy", "medium",
                "hard"). Not strictly validated against a fixed list
                here so new difficulty tiers can be added without
                changing this class.
            correct_suspect: Name/id of the suspect who is actually
                guilty. Used later to check the player's final
                accusation.
            suspects: Initial list of suspect names/ids. Defaults to
                an empty list.
            evidence: Initial list of evidence items. Defaults to an
                empty list.
            clues: Initial list of clue items. Defaults to an empty
                list.
            locations: Initial list of location ids (see
                `game.location.Location`) associated with this case.
                Defaults to an empty list. Mirrors `evidence`/`clues`:
                `Case` only stores the ids, never `Location` objects
                themselves -- those remain owned by `LocationManager`.
            status: Initial lifecycle status. Must be one of
                `VALID_STATUSES`. Defaults to "not_started".

        Raises:
            ValueError: If any required string field is empty/not a
                string, or if `status` is not a recognized value.
        """
        for field_name, value in (
            ("case_id", case_id),
            ("title", title),
            ("description", description),
            ("location", location),
            ("crime_type", crime_type),
            ("difficulty", difficulty),
            ("correct_suspect", correct_suspect),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")

        if status not in VALID_STATUSES:
            raise ValueError(
                f"status must be one of {VALID_STATUSES}, got {status!r}"
            )

        self.case_id: str = case_id
        self.title: str = title
        self.description: str = description
        self.location: str = location
        self.crime_type: str = crime_type
        self.difficulty: str = difficulty
        self.correct_suspect: str = correct_suspect

        self.suspects: List[str] = list(suspects) if suspects else []
        self.evidence: List[str] = list(evidence) if evidence else []
        self.clues: List[str] = list(clues) if clues else []
        self.locations: List[str] = list(locations) if locations else []
        self.status: str = status

    # -- Mutation helpers ---------------------------------------------

    def add_suspect(self, suspect: str) -> None:
        """Add a suspect to the case if not already present.

        Args:
            suspect: Name/id of the suspect.

        Raises:
            ValueError: If `suspect` is empty or not a string.
        """
        if not isinstance(suspect, str) or not suspect.strip():
            raise ValueError("suspect must be a non-empty string")
        if suspect not in self.suspects:
            self.suspects.append(suspect)

    def add_evidence(self, evidence: str) -> None:
        """Add an evidence item to the case if not already present.

        Args:
            evidence: Description/id of the evidence.

        Raises:
            ValueError: If `evidence` is empty or not a string.
        """
        if not isinstance(evidence, str) or not evidence.strip():
            raise ValueError("evidence must be a non-empty string")
        if evidence not in self.evidence:
            self.evidence.append(evidence)

    def add_clue(self, clue: str) -> None:
        """Add a clue to the case if not already present.

        Args:
            clue: Description/id of the clue.

        Raises:
            ValueError: If `clue` is empty or not a string.
        """
        if not isinstance(clue, str) or not clue.strip():
            raise ValueError("clue must be a non-empty string")
        if clue not in self.clues:
            self.clues.append(clue)

    def add_location(self, location_id: str) -> None:
        """Associate a location id with the case if not already present.

        Mirrors `add_evidence`/`add_clue`: only the id is stored here.
        The actual `Location` object stays owned by `LocationManager`.

        Args:
            location_id: Id of the location (see `game.location.Location`).

        Raises:
            ValueError: If `location_id` is empty or not a string.
        """
        if not isinstance(location_id, str) or not location_id.strip():
            raise ValueError("location_id must be a non-empty string")
        if location_id not in self.locations:
            self.locations.append(location_id)

    # -- Status management ----------------------------------------------

    def start(self) -> None:
        """Mark the case as in progress.

        Raises:
            RuntimeError: If the case has already been solved or
                failed.
        """
        if self.status in ("solved", "failed"):
            raise RuntimeError(
                f"Cannot start case '{self.case_id}': already {self.status}"
            )
        self.status = "in_progress"

    def complete_case(self, accused_suspect: str) -> bool:
        """Attempt to complete the case with a final accusation.

        Args:
            accused_suspect: The suspect the player is accusing.

        Returns:
            True if `accused_suspect` matches `correct_suspect` (the
            case is marked "solved"); False otherwise (the case is
            marked "failed").

        Raises:
            ValueError: If `accused_suspect` is empty or not a
                string.
            RuntimeError: If the case is not currently in progress.
        """
        if not isinstance(accused_suspect, str) or not accused_suspect.strip():
            raise ValueError("accused_suspect must be a non-empty string")
        if self.status != "in_progress":
            raise RuntimeError(
                f"Cannot complete case '{self.case_id}': "
                f"status is '{self.status}', expected 'in_progress'"
            )

        is_correct = accused_suspect == self.correct_suspect
        self.status = "solved" if is_correct else "failed"
        return is_correct

    def is_solved(self) -> bool:
        """Return True if the case's status is 'solved'."""
        return self.status == "solved"

    def get_status(self) -> str:
        """Return the case's current lifecycle status."""
        return self.status

    # -- Info retrieval ---------------------------------------------------

    def get_info(self) -> Dict[str, Any]:
        """Return a summary of the case's public information.

        Deliberately omits `correct_suspect` so it isn't accidentally
        leaked to UI code before the case is solved.

        Returns:
            A dictionary describing the case's metadata and current
            progress (suspects, evidence, and clue counts/lists).
        """
        return {
            "case_id": self.case_id,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "crime_type": self.crime_type,
            "difficulty": self.difficulty,
            "status": self.status,
            "suspects": list(self.suspects),
            "evidence": list(self.evidence),
            "clues": list(self.clues),
            "locations": list(self.locations),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Return the full case data as a dictionary, including the
        solution. Intended for saving to disk, not for display to
        the player mid-case.
        """
        data = self.get_info()
        data["correct_suspect"] = self.correct_suspect
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Case":
        """Build a `Case` from a plain dictionary (e.g. parsed JSON).

        Args:
            data: Dictionary containing at least the required case
                fields (case_id, title, description, location,
                crime_type, difficulty, correct_suspect). Optional
                fields (suspects, evidence, clues, status) fall back
                to their `Case.__init__` defaults if missing.

        Returns:
            A new `Case` instance.

        Raises:
            KeyError: If a required field is missing from `data`.
            ValueError: If a field has an invalid value.
        """
        required = (
            "case_id",
            "title",
            "description",
            "location",
            "crime_type",
            "difficulty",
            "correct_suspect",
        )
        missing = [field for field in required if field not in data]
        if missing:
            raise KeyError(f"Missing required case field(s): {missing}")

        return cls(
            case_id=data["case_id"],
            title=data["title"],
            description=data["description"],
            location=data["location"],
            crime_type=data["crime_type"],
            difficulty=data["difficulty"],
            correct_suspect=data["correct_suspect"],
            suspects=data.get("suspects", []),
            evidence=data.get("evidence", []),
            clues=data.get("clues", []),
            locations=data.get("locations", []),
            status=data.get("status", "not_started"),
        )

    def __repr__(self) -> str:
        return (
            f"Case(case_id={self.case_id!r}, title={self.title!r}, "
            f"status={self.status!r})"
        )


class CaseManager:
    """Loads and manages a collection of `Case` objects.

    Cases are typically loaded from JSON files in a directory (by
    default the project's `cases/` folder), but cases can also be
    added directly via `add_case` -- useful for tests or
    programmatically generated cases.
    """

    def __init__(self, cases_dir: Optional[str] = None) -> None:
        """Create a case manager.

        Args:
            cases_dir: Directory to load case JSON files from. If
                omitted, defaults to the `cases/` directory at the
                project root (relative to this file's location).
        """
        if cases_dir is None:
            cases_dir = str(Path(__file__).resolve().parent.parent / "cases")

        self.cases_dir: Path = Path(cases_dir)
        self._cases: Dict[str, Case] = {}
        self._load_errors: List[str] = []

    def add_case(self, case: Case) -> None:
        """Register a `Case` object directly with the manager.

        Args:
            case: The `Case` instance to add.

        Raises:
            TypeError: If `case` is not a `Case` instance.
            ValueError: If a case with the same `case_id` is already
                registered.
        """
        if not isinstance(case, Case):
            raise TypeError("case must be a Case instance")
        if case.case_id in self._cases:
            raise ValueError(f"Case with id '{case.case_id}' already exists")
        self._cases[case.case_id] = case

    def load_case_from_file(self, file_path: Path) -> Optional[Case]:
        """Load a single case from a JSON file.

        Invalid or unreadable files do not raise -- the error is
        recorded (see `get_load_errors`) and None is returned, so a
        single bad file doesn't stop the rest of the directory from
        loading.

        Args:
            file_path: Path to a `.json` case file.

        Returns:
            The loaded `Case`, or None if loading failed.
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            self._load_errors.append(f"{file_path}: file not found")
            return None
        except json.JSONDecodeError as exc:
            self._load_errors.append(f"{file_path}: invalid JSON ({exc})")
            return None

        try:
            case = Case.from_dict(data)
        except (KeyError, ValueError, TypeError) as exc:
            self._load_errors.append(f"{file_path}: invalid case data ({exc})")
            return None

        try:
            self.add_case(case)
        except ValueError as exc:
            self._load_errors.append(f"{file_path}: {exc}")
            return None

        return case

    def load_all_cases(self) -> List[Case]:
        """Load every `.json` file in `cases_dir` as a `Case`.

        Missing directories or unreadable files are handled
        gracefully: they're recorded via `get_load_errors` rather
        than raising.

        Returns:
            List of successfully loaded `Case` objects (newly loaded
            in this call).
        """
        if not self.cases_dir.exists():
            self._load_errors.append(
                f"{self.cases_dir}: cases directory does not exist"
            )
            return []

        loaded: List[Case] = []
        for file_path in sorted(self.cases_dir.glob("*.json")):
            case = self.load_case_from_file(file_path)
            if case is not None:
                loaded.append(case)

        return loaded

    def get_case(self, case_id: str) -> Optional[Case]:
        """Retrieve a loaded case by id, or None if not found."""
        return self._cases.get(case_id)

    def get_all_cases(self) -> List[Case]:
        """Return all currently loaded cases."""
        return list(self._cases.values())

    def get_cases_by_difficulty(self, difficulty: str) -> List[Case]:
        """Return all loaded cases matching the given difficulty."""
        return [c for c in self._cases.values() if c.difficulty == difficulty]

    def get_load_errors(self) -> List[str]:
        """Return a list of human-readable errors from failed loads."""
        return list(self._load_errors)

    def __len__(self) -> int:
        return len(self._cases)

    def __repr__(self) -> str:
        return f"CaseManager(cases_dir={str(self.cases_dir)!r}, loaded={len(self)})"
