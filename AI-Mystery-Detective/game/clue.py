"""
Clue module for AI Mystery Detective.

Defines two classes:

- `Clue`: represents a single clue discovered during an
  investigation (what it is, where/how it was found, its importance,
  and any evidence or suspects it's linked to).
- `ClueManager`: manages a collection of `Clue` objects and can load
  them from JSON files.

This module is intentionally independent of any UI or AI code. It
does not decide who's guilty or reason about connections -- it only
models and manages clue data. It mirrors the structure of
`game.evidence.Evidence`/`EvidenceManager` and
`game.suspect.Suspect`/`SuspectManager` so the three modules can be
used together consistently, without requiring any of them to import
each other at runtime.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Importance is validated against a fixed vocabulary, matching
# `game.evidence.VALID_IMPORTANCE_LEVELS`, since gameplay logic (and
# later, AI hint generation) will likely branch on it.
VALID_IMPORTANCE_LEVELS = ("low", "medium", "high", "critical")


class Clue:
    """Represents a single clue uncovered during an investigation.

    A `Clue` tracks whether it has been discovered by the player, and
    deliberately withholds its more revealing details (description,
    importance, linked evidence/suspects) from `get_info()` until it
    has been -- consistent with how `Evidence.get_info()` behaves, so
    UI code can't accidentally leak the solution by inspecting clues
    the player hasn't found yet.
    """

    def __init__(
        self,
        clue_id: str,
        description: str,
        source: str,
        location: str,
        importance: str = "low",
        discovered: bool = False,
        related_evidence: Optional[List[str]] = None,
        related_suspects: Optional[List[str]] = None,
    ) -> None:
        """Create a new clue.

        Args:
            clue_id: Unique identifier for this clue.
            description: What the clue actually is/reveals. Withheld
                from `get_info()` until discovered.
            source: Where the clue came from (e.g. "suspect
                testimony", "crime scene inspection").
            location: Where the clue was/will be found.
            importance: How significant the clue is. Must be one of
                `VALID_IMPORTANCE_LEVELS`. Defaults to "low".
            discovered: Whether the player has already found this
                clue. Defaults to False.
            related_evidence: Evidence ids this clue connects to.
                Defaults to an empty list. Withheld from `get_info()`
                until discovered.
            related_suspects: Suspect names/ids this clue connects
                to. Defaults to an empty list. Withheld from
                `get_info()` until discovered.

        Raises:
            ValueError: If a required string field is empty/not a
                string, or if `importance` isn't a recognized level.
        """
        for field_name, value in (
            ("clue_id", clue_id),
            ("description", description),
            ("source", source),
            ("location", location),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")

        if importance not in VALID_IMPORTANCE_LEVELS:
            raise ValueError(
                f"importance must be one of {VALID_IMPORTANCE_LEVELS}, "
                f"got {importance!r}"
            )

        if not isinstance(discovered, bool):
            raise ValueError("discovered must be a boolean")

        self.clue_id: str = clue_id
        self.description: str = description
        self.source: str = source
        self.location: str = location
        self.importance: str = importance
        self.discovered: bool = discovered
        self.related_evidence: List[str] = (
            list(related_evidence) if related_evidence else []
        )
        self.related_suspects: List[str] = (
            list(related_suspects) if related_suspects else []
        )

    # -- Discovery ----------------------------------------------------------

    def discover(self) -> None:
        """Mark this clue as discovered by the player.

        Raises:
            RuntimeError: If the clue has already been discovered
                (guards against redundant discovery logic/double
                -counted rewards elsewhere).
        """
        if self.discovered:
            raise RuntimeError(f"Clue '{self.clue_id}' has already been discovered")
        self.discovered = True

    def is_discovered(self) -> bool:
        """Return whether this clue has been discovered."""
        return self.discovered

    # -- Linking --------------------------------------------------------------

    def link_evidence(self, evidence_id: str) -> None:
        """Link this clue to a piece of evidence (by id).

        Args:
            evidence_id: Id of the evidence to link.

        Raises:
            ValueError: If `evidence_id` is empty or not a string.
        """
        if not isinstance(evidence_id, str) or not evidence_id.strip():
            raise ValueError("evidence_id must be a non-empty string")
        if evidence_id not in self.related_evidence:
            self.related_evidence.append(evidence_id)

    def link_suspect(self, suspect: str) -> None:
        """Link this clue to a suspect (by name or id).

        Args:
            suspect: Name/id of the suspect to link.

        Raises:
            ValueError: If `suspect` is empty or not a string.
        """
        if not isinstance(suspect, str) or not suspect.strip():
            raise ValueError("suspect must be a non-empty string")
        if suspect not in self.related_suspects:
            self.related_suspects.append(suspect)

    # -- Importance -----------------------------------------------------------

    def update_importance(self, new_importance: str) -> None:
        """Update the clue's importance level.

        Args:
            new_importance: Must be one of `VALID_IMPORTANCE_LEVELS`.

        Raises:
            ValueError: If `new_importance` isn't a recognized level.
        """
        if new_importance not in VALID_IMPORTANCE_LEVELS:
            raise ValueError(
                f"new_importance must be one of {VALID_IMPORTANCE_LEVELS}, "
                f"got {new_importance!r}"
            )
        self.importance = new_importance

    # -- Info retrieval ---------------------------------------------------

    def get_info(self) -> Dict[str, Any]:
        """Return the clue's information, respecting discovery status.

        Before discovery, only the "surface" fields are returned
        (id, source, location, discovered=False) -- `description`,
        `importance`, `related_evidence`, and `related_suspects` are
        withheld so the solution isn't leaked before the player
        actually finds the clue in-game. After discovery, the full
        profile is returned.

        Returns:
            A dictionary describing the clue, with detail appropriate
            to its discovery status.
        """
        info: Dict[str, Any] = {
            "clue_id": self.clue_id,
            "source": self.source,
            "location": self.location,
            "discovered": self.discovered,
        }
        if self.discovered:
            info["description"] = self.description
            info["importance"] = self.importance
            info["related_evidence"] = list(self.related_evidence)
            info["related_suspects"] = list(self.related_suspects)
        return info

    def to_dict(self) -> Dict[str, Any]:
        """Return the full clue data as a dictionary (for saving).

        Unlike `get_info()`, this always includes every field
        regardless of discovery status -- it's meant for persistence
        (save files, case authoring), not for display to the player.
        """
        return {
            "clue_id": self.clue_id,
            "description": self.description,
            "source": self.source,
            "location": self.location,
            "importance": self.importance,
            "discovered": self.discovered,
            "related_evidence": list(self.related_evidence),
            "related_suspects": list(self.related_suspects),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Clue":
        """Build a `Clue` from a plain dictionary (e.g. parsed JSON).

        Args:
            data: Dictionary containing at least the required fields
                (clue_id, description, source, location). Optional
                fields (importance, discovered, related_evidence,
                related_suspects) fall back to their
                `Clue.__init__` defaults if missing.

        Returns:
            A new `Clue` instance.

        Raises:
            KeyError: If a required field is missing from `data`.
            ValueError: If a field has an invalid value.
        """
        required = ("clue_id", "description", "source", "location")
        missing = [field for field in required if field not in data]
        if missing:
            raise KeyError(f"Missing required clue field(s): {missing}")

        return cls(
            clue_id=data["clue_id"],
            description=data["description"],
            source=data["source"],
            location=data["location"],
            importance=data.get("importance", "low"),
            discovered=data.get("discovered", False),
            related_evidence=data.get("related_evidence", []),
            related_suspects=data.get("related_suspects", []),
        )

    def __repr__(self) -> str:
        return (
            f"Clue(clue_id={self.clue_id!r}, source={self.source!r}, "
            f"discovered={self.discovered})"
        )


class ClueManager:
    """Manages a collection of `Clue` objects.

    Clues can be added directly via `add_clue`, or loaded from JSON
    files. Each JSON file may contain either a single clue object or
    a list of clue objects, which makes it easy to keep one file per
    case.
    """

    def __init__(self, clues_dir: Optional[str] = None) -> None:
        """Create a clue manager.

        Args:
            clues_dir: Optional default directory to load clue JSON
                files from when `load_all_clues()` is called without
                an explicit directory. No directory is assumed by
                default, since clue data may be organized per-case
                rather than in one fixed folder.
        """
        self.clues_dir: Optional[Path] = Path(clues_dir) if clues_dir else None
        self._clues: Dict[str, Clue] = {}
        self._load_errors: List[str] = []

    def add_clue(self, clue: Clue) -> None:
        """Register a `Clue` object directly with the manager.

        Args:
            clue: The `Clue` instance to add.

        Raises:
            TypeError: If `clue` is not a `Clue` instance.
            ValueError: If a clue with the same `clue_id` is already
                registered.
        """
        if not isinstance(clue, Clue):
            raise TypeError("clue must be a Clue instance")
        if clue.clue_id in self._clues:
            raise ValueError(f"Clue with id '{clue.clue_id}' already exists")
        self._clues[clue.clue_id] = clue

    def load_clue_from_file(self, file_path: Union[str, Path]) -> List[Clue]:
        """Load one or more clues from a single JSON file.

        The file may contain either a JSON object (one clue) or a
        JSON array of objects (multiple clues). Invalid or unreadable
        files do not raise -- errors are recorded (see
        `get_load_errors`) and an empty list is returned, so a single
        bad file doesn't stop the rest of a directory from loading.

        Args:
            file_path: Path to a `.json` clue file.

        Returns:
            List of successfully loaded `Clue` objects from this file
            (empty if loading failed entirely).
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

        loaded: List[Clue] = []
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                self._load_errors.append(
                    f"{file_path}[{index}]: expected an object, got {type(record).__name__}"
                )
                continue
            try:
                clue = Clue.from_dict(record)
            except (KeyError, ValueError, TypeError) as exc:
                self._load_errors.append(f"{file_path}[{index}]: invalid clue data ({exc})")
                continue
            try:
                self.add_clue(clue)
            except ValueError as exc:
                self._load_errors.append(f"{file_path}[{index}]: {exc}")
                continue
            loaded.append(clue)

        return loaded

    def load_all_clues(self, directory: Optional[Union[str, Path]] = None) -> List[Clue]:
        """Load every `.json` file in a directory as clue data.

        Args:
            directory: Directory to scan. Falls back to
                `self.clues_dir` if omitted.

        Returns:
            List of successfully loaded `Clue` objects (newly loaded
            in this call).

        Raises:
            ValueError: If no directory is given and no default
                `clues_dir` was set.
        """
        target_dir = Path(directory) if directory is not None else self.clues_dir
        if target_dir is None:
            raise ValueError("No directory given and no default clues_dir was set")

        if not target_dir.exists():
            self._load_errors.append(f"{target_dir}: clues directory does not exist")
            return []

        loaded: List[Clue] = []
        for file_path in sorted(target_dir.glob("*.json")):
            loaded.extend(self.load_clue_from_file(file_path))

        return loaded

    def get_clue(self, clue_id: str) -> Optional[Clue]:
        """Retrieve a clue by id, or None if not found."""
        return self._clues.get(clue_id)

    def get_all_clues(self) -> List[Clue]:
        """Return all currently registered clues."""
        return list(self._clues.values())

    def get_discovered_clues(self) -> List[Clue]:
        """Return only clues the player has discovered."""
        return [c for c in self._clues.values() if c.discovered]

    def get_undiscovered_clues(self) -> List[Clue]:
        """Return only clues not yet discovered."""
        return [c for c in self._clues.values() if not c.discovered]

    def get_clues_by_suspect(self, suspect: str) -> List[Clue]:
        """Return discovered clues linked to a given suspect.

        Only considers discovered clues, since undiscovered clues'
        suspect links aren't meant to be queryable before the player
        finds them.
        """
        return [
            c for c in self._clues.values() if c.discovered and suspect in c.related_suspects
        ]

    def get_clues_by_evidence(self, evidence_id: str) -> List[Clue]:
        """Return discovered clues linked to a given evidence item.

        Only considers discovered clues, for the same reason as
        `get_clues_by_suspect`.
        """
        return [
            c
            for c in self._clues.values()
            if c.discovered and evidence_id in c.related_evidence
        ]

    def discover_clue(self, clue_id: str) -> Clue:
        """Look up a clue by id and mark it as discovered.

        Args:
            clue_id: Id of the clue to discover.

        Returns:
            The now-discovered `Clue` instance.

        Raises:
            KeyError: If no clue with that id is registered.
            RuntimeError: If the clue was already discovered.
        """
        clue = self._clues.get(clue_id)
        if clue is None:
            raise KeyError(f"No clue found with id '{clue_id}'")
        clue.discover()
        return clue

    def get_load_errors(self) -> List[str]:
        """Return a list of human-readable errors from failed loads."""
        return list(self._load_errors)

    def __len__(self) -> int:
        return len(self._clues)

    def __repr__(self) -> str:
        return f"ClueManager(loaded={len(self)})"
