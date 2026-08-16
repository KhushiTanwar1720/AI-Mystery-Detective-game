"""
Location module for AI Mystery Detective.

Defines two classes:

- `Location`: represents a single explorable place within a mystery
  case (its description, type, connections to other locations, and
  which evidence/clue ids are potentially findable there).
- `LocationManager`: manages a collection of `Location` objects and
  can load them from JSON files.

This module is intentionally independent of any UI or AI code, and
does not duplicate `Evidence`/`Clue`/`Investigation` logic. A
`Location` only *references* evidence/clue ids (by string id) -- it
does not own `Evidence`/`Clue` objects, does not know whether they've
actually been discovered, and never marks anything as discovered on
its own. Discovery remains entirely the responsibility of
`EvidenceManager`/`ClueManager` (via `Investigation.discover_evidence`/
`discover_clue`), exactly as it already is for the simpler
free-text-location model `Investigation.inspect_location()` uses.

`Location.visit()` / `get_location_info()` simply expose *which*
evidence/clue ids are associated with a location, so a caller (e.g. a
future UI layer, or `GameController`) can decide what to surface to
the player and what to pass to `Investigation.discover_evidence()` /
`discover_clue()`. This module does not import `game.investigation`
(or vice versa) to avoid a circular import; `Investigation` tracking
visits by location name (`get_visited_locations()`) and `Location`
tracking visits by location id are two independent, compatible
concepts -- a caller integrating both simply visits a `Location` and
then calls `Investigation.inspect_location()`/`discover_evidence()`/
`discover_clue()` with the ids it exposes.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Location type is kept loose (any non-empty string is accepted), the
# same design choice `Evidence.evidence_type` and `Case.crime_type`
# make, so new categories of location can be added without changing
# this class.


class Location:
    """Represents a single explorable location within a mystery case.

    A `Location` is a data-holding object with light behavior for
    tracking visits and managing its connections to other locations
    and the evidence/clue ids potentially available there. It does
    not decide what's "discovered" -- that stays the responsibility
    of `EvidenceManager`/`ClueManager`/`Investigation`.
    """

    def __init__(
        self,
        location_id: str,
        name: str,
        description: str,
        location_type: str,
        connected_locations: Optional[List[str]] = None,
        available_evidence: Optional[List[str]] = None,
        available_clues: Optional[List[str]] = None,
        visited: bool = False,
        visit_count: int = 0,
    ) -> None:
        """Create a new location.

        Args:
            location_id: Unique identifier for the location.
            name: Short human-readable location name.
            description: Longer narrative description of the place.
            location_type: Category of location (e.g. "mansion",
                "room", "outdoor"). Not strictly validated against a
                fixed list so new location types can be added freely.
            connected_locations: Initial list of ids of locations
                reachable from this one. Defaults to an empty list.
            available_evidence: Initial list of evidence ids
                potentially findable at this location. Defaults to an
                empty list.
            available_clues: Initial list of clue ids potentially
                findable at this location. Defaults to an empty list.
            visited: Whether this location starts out already
                visited. Defaults to False.
            visit_count: Initial visit count. Must be a non-negative
                integer. Defaults to 0.

        Raises:
            ValueError: If a required string field is empty/not a
                string, or if `visit_count` is negative or not an
                integer.
        """
        for field_name, value in (
            ("location_id", location_id),
            ("name", name),
            ("description", description),
            ("location_type", location_type),
        ):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")

        if not isinstance(visit_count, int) or isinstance(visit_count, bool):
            raise ValueError("visit_count must be an integer")
        if visit_count < 0:
            raise ValueError("visit_count must be non-negative")

        self.location_id: str = location_id
        self.name: str = name
        self.description: str = description
        self.location_type: str = location_type

        self.connected_locations: List[str] = (
            list(dict.fromkeys(connected_locations)) if connected_locations else []
        )
        self.available_evidence: List[str] = (
            list(dict.fromkeys(available_evidence)) if available_evidence else []
        )
        self.available_clues: List[str] = (
            list(dict.fromkeys(available_clues)) if available_clues else []
        )

        self.visited: bool = bool(visited)
        self.visit_count: int = visit_count

    # -- Visiting -------------------------------------------------------------

    def visit(self) -> Dict[str, Any]:
        """Visit this location, marking it visited and incrementing its count.

        Does not discover anything by itself -- it only reports which
        evidence/clue ids are potentially available here, leaving the
        caller to decide what (if anything) to actually discover via
        `Investigation`/`EvidenceManager`/`ClueManager`.

        Returns:
            The location's info snapshot (see `get_location_info()`),
            for convenience, after recording the visit.
        """
        self.visited = True
        self.visit_count += 1
        return self.get_location_info()

    def leave(self) -> None:
        """Leave this location.

        `Location` doesn't track a global "current location" itself
        (that's session-level state, owned by the caller/
        `Investigation`), so leaving doesn't need to mutate anything
        here. This method exists mainly to make the visit/leave
        lifecycle explicit and symmetrical for callers, and as a hook
        future subclasses could extend (e.g. to log a departure
        timestamp) without changing this class's public API.
        """
        return None

    def is_visited(self) -> bool:
        """Return whether this location has been visited at least once."""
        return self.visited

    # -- Connections ------------------------------------------------------------

    def connect_location(self, location_id: str) -> bool:
        """Add a connection from this location to another, by id.

        Args:
            location_id: Id of the location to connect to. Must be a
                non-empty string, and cannot be this location's own
                id (a location cannot connect to itself).

        Returns:
            True if a new connection was added, False if the
            connection already existed (duplicates are silently
            ignored rather than raising, so callers can connect
            idempotently).

        Raises:
            ValueError: If `location_id` is empty, not a string, or
                equal to this location's own id.
        """
        if not isinstance(location_id, str) or not location_id.strip():
            raise ValueError("location_id must be a non-empty string")
        if location_id == self.location_id:
            raise ValueError("a location cannot connect to itself")

        if location_id in self.connected_locations:
            return False

        self.connected_locations.append(location_id)
        return True

    def disconnect_location(self, location_id: str) -> bool:
        """Remove a connection from this location to another, by id.

        Args:
            location_id: Id of the connected location to remove.

        Returns:
            True if a connection was removed, False if no such
            connection existed.

        Raises:
            ValueError: If `location_id` is empty or not a string.
        """
        if not isinstance(location_id, str) or not location_id.strip():
            raise ValueError("location_id must be a non-empty string")

        if location_id not in self.connected_locations:
            return False

        self.connected_locations.remove(location_id)
        return True

    def get_connected_locations(self) -> List[str]:
        """Return the ids of locations connected to this one."""
        return list(self.connected_locations)

    # -- Evidence / clue references ----------------------------------------------

    def add_evidence(self, evidence_id: str) -> bool:
        """Reference an evidence id as potentially available here.

        This only records that the evidence *could* be found at this
        location -- it does not create, own, or discover an
        `Evidence` object. Discovery is handled entirely by
        `EvidenceManager`/`Investigation`.

        Args:
            evidence_id: Id of the evidence to reference.

        Returns:
            True if the id was newly added, False if it was already
            referenced (duplicates are ignored, not raised).

        Raises:
            ValueError: If `evidence_id` is empty or not a string.
        """
        if not isinstance(evidence_id, str) or not evidence_id.strip():
            raise ValueError("evidence_id must be a non-empty string")

        if evidence_id in self.available_evidence:
            return False

        self.available_evidence.append(evidence_id)
        return True

    def add_clue(self, clue_id: str) -> bool:
        """Reference a clue id as potentially available here.

        Same semantics as `add_evidence()`, for clues.

        Args:
            clue_id: Id of the clue to reference.

        Returns:
            True if the id was newly added, False if it was already
            referenced.

        Raises:
            ValueError: If `clue_id` is empty or not a string.
        """
        if not isinstance(clue_id, str) or not clue_id.strip():
            raise ValueError("clue_id must be a non-empty string")

        if clue_id in self.available_clues:
            return False

        self.available_clues.append(clue_id)
        return True

    def get_available_evidence(self) -> List[str]:
        """Return the evidence ids potentially available at this location."""
        return list(self.available_evidence)

    def get_available_clues(self) -> List[str]:
        """Return the clue ids potentially available at this location."""
        return list(self.available_clues)

    # -- Info retrieval / reset ---------------------------------------------------

    def get_location_info(self) -> Dict[str, Any]:
        """Return a dictionary summarizing this location's current state.

        Unlike `Evidence.get_info()`/`Clue.get_info()`, a location's
        info isn't discovery-gated -- the *place* is either reachable
        or it isn't; it's the evidence/clue *ids* referenced here
        (not their content) that are exposed, so nothing about the
        solution is leaked. Actual evidence/clue detail stays gated
        behind their own `get_info()`.

        Returns:
            A dictionary describing the location's identity,
            connections, referenced evidence/clue ids, and visit
            state.
        """
        return {
            "location_id": self.location_id,
            "name": self.name,
            "description": self.description,
            "location_type": self.location_type,
            "connected_locations": list(self.connected_locations),
            "available_evidence": list(self.available_evidence),
            "available_clues": list(self.available_clues),
            "visited": self.visited,
            "visit_count": self.visit_count,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Return the full location data as a dictionary (for saving)."""
        return self.get_location_info()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Location":
        """Build a `Location` from a plain dictionary (e.g. parsed JSON).

        Args:
            data: Dictionary containing at least the required fields
                (location_id, name, description, location_type).
                Optional fields (connected_locations,
                available_evidence, available_clues, visited,
                visit_count) fall back to their `Location.__init__`
                defaults if missing.

        Returns:
            A new `Location` instance.

        Raises:
            KeyError: If a required field is missing from `data`.
            ValueError: If a field has an invalid value.
        """
        required = ("location_id", "name", "description", "location_type")
        missing = [field for field in required if field not in data]
        if missing:
            raise KeyError(f"Missing required location field(s): {missing}")

        return cls(
            location_id=data["location_id"],
            name=data["name"],
            description=data["description"],
            location_type=data["location_type"],
            connected_locations=data.get("connected_locations", []),
            available_evidence=data.get("available_evidence", []),
            available_clues=data.get("available_clues", []),
            visited=data.get("visited", False),
            visit_count=data.get("visit_count", 0),
        )

    def reset_location(self) -> None:
        """Reset this location's visit state back to unvisited.

        Only resets visit tracking (`visited`/`visit_count`) --
        connections and evidence/clue references are structural case
        data, not per-playthrough progress, so they're left intact.
        """
        self.visited = False
        self.visit_count = 0

    def __repr__(self) -> str:
        return (
            f"Location(location_id={self.location_id!r}, name={self.name!r}, "
            f"visited={self.visited}, visit_count={self.visit_count})"
        )


class LocationManager:
    """Manages a collection of `Location` objects.

    Locations can be added directly via `add_location`, or loaded
    from JSON files (one location per object, or a list of location
    objects per file) -- mirroring the loading conventions already
    used by `EvidenceManager`/`ClueManager`/`SuspectManager`.
    """

    def __init__(self, locations_dir: Optional[Union[str, Path]] = None) -> None:
        """Create a location manager.

        Args:
            locations_dir: Optional default directory to load location
                JSON files from when `load_all_locations()` is called
                without an explicit directory. No directory is
                assumed by default, since location data may be
                organized per-case rather than in one fixed folder
                (matching `EvidenceManager`'s/`ClueManager`'s design).
        """
        self.locations_dir: Optional[Path] = Path(locations_dir) if locations_dir else None
        self._locations: Dict[str, Location] = {}
        self._load_errors: List[str] = []

    # -- Registration -------------------------------------------------------------

    def add_location(self, location: Location) -> None:
        """Register a `Location` object directly with the manager.

        Args:
            location: The `Location` instance to add.

        Raises:
            TypeError: If `location` is not a `Location` instance.
            ValueError: If a location with the same `location_id` is
                already registered.
        """
        if not isinstance(location, Location):
            raise TypeError("location must be a Location instance")
        if location.location_id in self._locations:
            raise ValueError(
                f"Location with id '{location.location_id}' already exists"
            )
        self._locations[location.location_id] = location

    def remove_location(self, location_id: str) -> bool:
        """Remove a registered location by id, if it exists.

        Also cleans up any connections other locations have pointing
        to the removed location, so `LocationManager` never ends up
        holding dangling references after a removal.

        Args:
            location_id: Id of the location to remove.

        Returns:
            True if the location existed and was removed, False
            otherwise.
        """
        if location_id not in self._locations:
            return False

        del self._locations[location_id]
        for other in self._locations.values():
            if location_id in other.connected_locations:
                other.connected_locations.remove(location_id)
        return True

    def location_exists(self, location_id: str) -> bool:
        """Return True if a location with `location_id` is registered."""
        return location_id in self._locations

    def get_location(self, location_id: str) -> Optional[Location]:
        """Retrieve a location by id, or None if not found."""
        return self._locations.get(location_id)

    def get_all_locations(self) -> List[Location]:
        """Return all currently registered locations."""
        return list(self._locations.values())

    # -- Connections --------------------------------------------------------------

    def connect_locations(self, location_id_a: str, location_id_b: str, bidirectional: bool = True) -> bool:
        """Connect two registered locations to each other.

        Args:
            location_id_a: Id of the first location.
            location_id_b: Id of the second location.
            bidirectional: If True (the default), the connection is
                added in both directions (a->b and b->a). If False,
                only a->b is added.

        Returns:
            True if at least one new connection was added, False if
            the connection(s) already existed.

        Raises:
            ValueError: If either id is empty/not a string, or if the
                two ids are identical.
            KeyError: If either location isn't registered.
        """
        if not isinstance(location_id_a, str) or not location_id_a.strip():
            raise ValueError("location_id_a must be a non-empty string")
        if not isinstance(location_id_b, str) or not location_id_b.strip():
            raise ValueError("location_id_b must be a non-empty string")
        if location_id_a == location_id_b:
            raise ValueError("a location cannot connect to itself")

        loc_a = self._locations.get(location_id_a)
        loc_b = self._locations.get(location_id_b)
        if loc_a is None:
            raise KeyError(f"No location found with id '{location_id_a}'")
        if loc_b is None:
            raise KeyError(f"No location found with id '{location_id_b}'")

        added = loc_a.connect_location(location_id_b)
        if bidirectional:
            added = loc_b.connect_location(location_id_a) or added

        return added

    # -- Loading --------------------------------------------------------------

    def _validate_location_data(self, data: Any) -> None:
        """Validate that `data` has the minimal shape a location record needs.

        Raises:
            TypeError: If `data` isn't a dict.
            KeyError: If a required field is missing.
        """
        if not isinstance(data, dict):
            raise TypeError(f"expected an object, got {type(data).__name__}")

        required = ("location_id", "name", "description", "location_type")
        missing = [field for field in required if field not in data]
        if missing:
            raise KeyError(f"Missing required location field(s): {missing}")

    def load_location_from_file(self, file_path: Union[str, Path]) -> List[Location]:
        """Load one or more locations from a single JSON file.

        The file may contain either a JSON object (one location) or a
        JSON array of objects (multiple locations). Invalid or
        unreadable files/entries do not raise -- errors are recorded
        (see `get_load_errors`) and a partial (possibly empty) list is
        returned, so a single bad file/entry doesn't stop the rest of
        a directory -- or the rest of the file -- from loading.

        Args:
            file_path: Path to a `.json` location file.

        Returns:
            List of successfully loaded `Location` objects from this
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

        loaded: List[Location] = []
        for index, record in enumerate(records):
            try:
                self._validate_location_data(record)
                location = Location.from_dict(record)
            except (KeyError, ValueError, TypeError) as exc:
                self._load_errors.append(f"{file_path}[{index}]: invalid location data ({exc})")
                continue
            try:
                self.add_location(location)
            except ValueError as exc:
                self._load_errors.append(f"{file_path}[{index}]: {exc}")
                continue
            loaded.append(location)

        return loaded

    def load_all_locations(self, directory: Optional[Union[str, Path]] = None) -> List[Location]:
        """Load every `.json` file in a directory as location data.

        Args:
            directory: Directory to scan. Falls back to
                `self.locations_dir` if omitted.

        Returns:
            List of successfully loaded `Location` objects (newly
            loaded in this call).

        Raises:
            ValueError: If no directory is given and no default
                `locations_dir` was set.
        """
        target_dir = Path(directory) if directory is not None else self.locations_dir
        if target_dir is None:
            raise ValueError(
                "No directory given and no default locations_dir was set"
            )

        if not target_dir.exists():
            self._load_errors.append(f"{target_dir}: locations directory does not exist")
            return []

        loaded: List[Location] = []
        for file_path in sorted(target_dir.glob("*.json")):
            loaded.extend(self.load_location_from_file(file_path))

        return loaded

    def get_load_errors(self) -> List[str]:
        """Return a list of human-readable errors from failed loads."""
        return list(self._load_errors)

    def __len__(self) -> int:
        return len(self._locations)

    def __repr__(self) -> str:
        return f"LocationManager(loaded={len(self)})"
