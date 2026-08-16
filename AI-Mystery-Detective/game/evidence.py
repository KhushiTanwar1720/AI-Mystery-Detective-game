"""
Evidence module for AI Mystery Detective.

Defines two classes:

- `Evidence`: represents a single piece of evidence within a mystery
  case (its description, type, importance, discovery status, and any
  suspects it's linked to).
- `EvidenceManager`: manages a collection of `Evidence` objects and
  can load them from JSON files.

This module is intentionally independent of any UI or AI code. It
does not decide who's guilty or analyze clues -- it only models and
manages evidence data. It's designed to be used alongside
`game.case.Case`/`CaseManager` and `game.suspect.Suspect`/
`SuspectManager`, but does not require importing either to function.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Evidence type is kept loose (any non-empty string is accepted) so
# new categories can be added without changing this class, similar to
# how `Case.crime_type` is handled.

# Importance IS validated against a fixed vocabulary, since gameplay
# logic (and later, AI hint generation) will likely branch on it.
VALID_IMPORTANCE_LEVELS = ("low", "medium", "high", "critical")


class Evidence:
    """Represents a single piece of evidence in a mystery case.

    An `Evidence` object tracks whether it has been discovered by the
    player, and deliberately withholds its more revealing details
    (description, importance, linked suspects) from `get_info()`
    until it has been. This keeps the module from accidentally
    leaking the solution to UI code that inspects evidence before the
    player has actually found it in-game.
    """

    def __init__(
        self,
        evidence_id: str,
        name: str,
        description: str,
        evidence_type: str,
        location_found: str,
        importance: str = "low",
        discovered: bool = False,
        related_suspects: Optional[List[str]] = None,
    ) -> None:
        """Create a new evidence item.

        Args:
            evidence_id: Unique identifier for this evidence item.
            name: Short display name (e.g. "Bloody Knife").
            description: Full description of the evidence. Withheld
                from `get_info()` until discovered.
            evidence_type: Category of evidence (e.g. "physical",
                "testimonial", "digital"). Not restricted to a fixed
                list so new categories can be added freely.
            location_found: Where the evidence was/will be found.
            importance: How significant the evidence is. Must be one
                of `VALID_IMPORTANCE_LEVELS`. Defaults to "low".
            discovered: Whether the player has already found this
                evidence. Defaults to False.
            related_suspects: Suspect names/ids this evidence links
                to. Defaults to an empty list. Withheld from
                `get_info()` until discovered, since it's often the
                whole point of finding the evidence.

        Raises:
            ValueError: If a required string field is empty/not a
                string, or if `importance` isn't a recognized level.
        """
        for field_name, value in (
            ("evidence_id", evidence_id),
            ("name", name),
            ("description", description),
            ("evidence_type", evidence_type),
            ("location_found", location_found),
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

        self.evidence_id: str = evidence_id
        self.name: str = name
        self.description: str = description
        self.evidence_type: str = evidence_type
        self.location_found: str = location_found
        self.importance: str = importance
        self.discovered: bool = discovered
        self.related_suspects: List[str] = (
            list(related_suspects) if related_suspects else []
        )

    # -- Discovery ----------------------------------------------------------

    def discover(self) -> None:
        """Mark this evidence as discovered by the player.

        Raises:
            RuntimeError: If the evidence has already been
                discovered (guards against redundant discovery
                logic/double-counted rewards elsewhere).
        """
        if self.discovered:
            raise RuntimeError(
                f"Evidence '{self.evidence_id}' has already been discovered"
            )
        self.discovered = True

    def is_discovered(self) -> bool:
        """Return whether this evidence has been discovered."""
        return self.discovered

    # -- Suspect linking ------------------------------------------------------

    def link_suspect(self, suspect: str) -> None:
        """Link this evidence to a suspect (by name or id).

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
        """Update the evidence's importance level.

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
        """Return the evidence's information, respecting discovery status.

        Before discovery, only the "surface" fields are returned
        (id, name, type, location, discovered=False) -- `description`,
        `importance`, and `related_suspects` are withheld so the
        solution isn't leaked before the player actually finds the
        evidence in-game. After discovery, the full profile is
        returned.

        Returns:
            A dictionary describing the evidence, with detail
            appropriate to its discovery status.
        """
        info: Dict[str, Any] = {
            "evidence_id": self.evidence_id,
            "name": self.name,
            "evidence_type": self.evidence_type,
            "location_found": self.location_found,
            "discovered": self.discovered,
        }
        if self.discovered:
            info["description"] = self.description
            info["importance"] = self.importance
            info["related_suspects"] = list(self.related_suspects)
        return info

    def to_dict(self) -> Dict[str, Any]:
        """Return the full evidence data as a dictionary (for saving).

        Unlike `get_info()`, this always includes every field
        regardless of discovery status -- it's meant for persistence
        (save files, case authoring), not for display to the player.
        """
        return {
            "evidence_id": self.evidence_id,
            "name": self.name,
            "description": self.description,
            "evidence_type": self.evidence_type,
            "location_found": self.location_found,
            "importance": self.importance,
            "discovered": self.discovered,
            "related_suspects": list(self.related_suspects),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Evidence":
        """Build an `Evidence` from a plain dictionary (e.g. parsed JSON).

        Args:
            data: Dictionary containing at least the required fields
                (evidence_id, name, description, evidence_type,
                location_found). Optional fields (importance,
                discovered, related_suspects) fall back to their
                `Evidence.__init__` defaults if missing.

        Returns:
            A new `Evidence` instance.

        Raises:
            KeyError: If a required field is missing from `data`.
            ValueError: If a field has an invalid value.
        """
        required = (
            "evidence_id",
            "name",
            "description",
            "evidence_type",
            "location_found",
        )
        missing = [field for field in required if field not in data]
        if missing:
            raise KeyError(f"Missing required evidence field(s): {missing}")

        return cls(
            evidence_id=data["evidence_id"],
            name=data["name"],
            description=data["description"],
            evidence_type=data["evidence_type"],
            location_found=data["location_found"],
            importance=data.get("importance", "low"),
            discovered=data.get("discovered", False),
            related_suspects=data.get("related_suspects", []),
        )

    def __repr__(self) -> str:
        return (
            f"Evidence(evidence_id={self.evidence_id!r}, name={self.name!r}, "
            f"discovered={self.discovered})"
        )


class EvidenceManager:
    """Manages a collection of `Evidence` objects.

    Evidence can be added directly via `add_evidence`, or loaded from
    JSON files. Each JSON file may contain either a single evidence
    object or a list of evidence objects, which makes it easy to keep
    one file per case.
    """

    def __init__(self, evidence_dir: Optional[str] = None) -> None:
        """Create an evidence manager.

        Args:
            evidence_dir: Optional default directory to load evidence
                JSON files from when `load_all_evidence()` is called
                without an explicit directory. No directory is
                assumed by default, since evidence data may be
                organized per-case rather than in one fixed folder.
        """
        self.evidence_dir: Optional[Path] = Path(evidence_dir) if evidence_dir else None
        self._evidence: Dict[str, Evidence] = {}
        self._load_errors: List[str] = []

    def add_evidence(self, evidence: Evidence) -> None:
        """Register an `Evidence` object directly with the manager.

        Args:
            evidence: The `Evidence` instance to add.

        Raises:
            TypeError: If `evidence` is not an `Evidence` instance.
            ValueError: If evidence with the same `evidence_id` is
                already registered.
        """
        if not isinstance(evidence, Evidence):
            raise TypeError("evidence must be an Evidence instance")
        if evidence.evidence_id in self._evidence:
            raise ValueError(
                f"Evidence with id '{evidence.evidence_id}' already exists"
            )
        self._evidence[evidence.evidence_id] = evidence

    def load_evidence_from_file(self, file_path: Union[str, Path]) -> List[Evidence]:
        """Load one or more evidence items from a single JSON file.

        The file may contain either a JSON object (one evidence item)
        or a JSON array of objects (multiple items). Invalid or
        unreadable files do not raise -- errors are recorded (see
        `get_load_errors`) and an empty list is returned, so a single
        bad file doesn't stop the rest of a directory from loading.

        Args:
            file_path: Path to a `.json` evidence file.

        Returns:
            List of successfully loaded `Evidence` objects from this
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

        loaded: List[Evidence] = []
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                self._load_errors.append(
                    f"{file_path}[{index}]: expected an object, got {type(record).__name__}"
                )
                continue
            try:
                evidence = Evidence.from_dict(record)
            except (KeyError, ValueError, TypeError) as exc:
                self._load_errors.append(f"{file_path}[{index}]: invalid evidence data ({exc})")
                continue
            try:
                self.add_evidence(evidence)
            except ValueError as exc:
                self._load_errors.append(f"{file_path}[{index}]: {exc}")
                continue
            loaded.append(evidence)

        return loaded

    def load_all_evidence(self, directory: Optional[Union[str, Path]] = None) -> List[Evidence]:
        """Load every `.json` file in a directory as evidence data.

        Args:
            directory: Directory to scan. Falls back to
                `self.evidence_dir` if omitted.

        Returns:
            List of successfully loaded `Evidence` objects (newly
            loaded in this call).

        Raises:
            ValueError: If no directory is given and no default
                `evidence_dir` was set.
        """
        target_dir = Path(directory) if directory is not None else self.evidence_dir
        if target_dir is None:
            raise ValueError(
                "No directory given and no default evidence_dir was set"
            )

        if not target_dir.exists():
            self._load_errors.append(f"{target_dir}: evidence directory does not exist")
            return []

        loaded: List[Evidence] = []
        for file_path in sorted(target_dir.glob("*.json")):
            loaded.extend(self.load_evidence_from_file(file_path))

        return loaded

    def get_evidence(self, evidence_id: str) -> Optional[Evidence]:
        """Retrieve an evidence item by id, or None if not found."""
        return self._evidence.get(evidence_id)

    def get_all_evidence(self) -> List[Evidence]:
        """Return all currently registered evidence items."""
        return list(self._evidence.values())

    def get_discovered_evidence(self) -> List[Evidence]:
        """Return only evidence items the player has discovered."""
        return [e for e in self._evidence.values() if e.discovered]

    def get_undiscovered_evidence(self) -> List[Evidence]:
        """Return only evidence items not yet discovered."""
        return [e for e in self._evidence.values() if not e.discovered]

    def get_evidence_by_suspect(self, suspect: str) -> List[Evidence]:
        """Return discovered evidence items linked to a given suspect.

        Only considers discovered evidence, since undiscovered
        evidence's suspect links aren't meant to be queryable before
        the player finds them.
        """
        return [
            e
            for e in self._evidence.values()
            if e.discovered and suspect in e.related_suspects
        ]

    def discover_evidence(self, evidence_id: str) -> Evidence:
        """Look up an evidence item by id and mark it as discovered.

        Args:
            evidence_id: Id of the evidence to discover.

        Returns:
            The now-discovered `Evidence` instance.

        Raises:
            KeyError: If no evidence with that id is registered.
            RuntimeError: If the evidence was already discovered.
        """
        evidence = self._evidence.get(evidence_id)
        if evidence is None:
            raise KeyError(f"No evidence found with id '{evidence_id}'")
        evidence.discover()
        return evidence

    def get_load_errors(self) -> List[str]:
        """Return a list of human-readable errors from failed loads."""
        return list(self._load_errors)

    def __len__(self) -> int:
        return len(self._evidence)

    def __repr__(self) -> str:
        return f"EvidenceManager(loaded={len(self)})"
