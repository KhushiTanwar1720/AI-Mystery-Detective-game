"""
Investigation module for AI Mystery Detective.

Defines the `Investigation` class, which drives a single play-through
of a `Case`: selecting the case, starting the investigation, letting
the player inspect locations, discover evidence and clues, examine
suspects and review their statements, and finally end the
investigation.

This module is the "game logic" layer that ties together
`game.case.Case`/`CaseManager`, `game.evidence.Evidence`/
`EvidenceManager`, `game.clue.Clue`/`ClueManager`, and
`game.suspect.Suspect`/`SuspectManager`. It is intentionally
independent of any UI or AI code: it does not render anything,
generate hints, or reason about who's guilty -- it only manages
investigation state, validates player actions, and records history.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from game.case import Case, CaseManager
from game.clue import Clue, ClueManager
from game.evidence import Evidence, EvidenceManager
from game.location import Location, LocationManager
from game.suspect import Suspect, SuspectManager

# Valid lifecycle states for an Investigation. Kept separate from
# `Case.status` (see `game.case.VALID_STATUSES`) because an
# investigation can be ended (e.g. abandoned by the player) without
# the underlying case itself being marked solved/failed.
VALID_INVESTIGATION_STATUSES = ("not_started", "active", "ended")


class Investigation:
    """Manages a single player's investigation of a `Case`.

    An `Investigation` does not own case/evidence/clue/suspect data
    directly -- it holds references to the `CaseManager`,
    `EvidenceManager`, `ClueManager`, and `SuspectManager` that do,
    and coordinates player actions against them:

    - `select_case` / `start_investigation` choose and begin a case.
    - `inspect_location` lets the player look around a place in the
      case, surfacing what (undiscovered or discovered) evidence and
      clues are known to be there.
    - `discover_evidence` / `discover_clue` mark specific items as
      found, guarding against duplicates and items that don't belong
      to the selected case.
    - `examine_suspect` / `review_statements` let the player look at
      a suspect's profile and testimony.
    - `get_progress` / `get_history` report on investigation state.
    - `end_investigation` closes out the session, optionally
      resolving the case with a final accusation.

    All actions are validated: invalid input raises `ValueError`,
    action taken in the wrong state raises `RuntimeError`, and
    references to unknown/out-of-case items raise `KeyError`. Every
    successful action is recorded in an internal history log,
    retrievable via `get_history()`.
    """

    def __init__(
        self,
        case_manager: CaseManager,
        evidence_manager: EvidenceManager,
        clue_manager: ClueManager,
        suspect_manager: SuspectManager,
        investigator: str = "Player",
        location_manager: Optional[LocationManager] = None,
    ) -> None:
        """Create a new investigation session.

        Args:
            case_manager: Source of `Case` objects to select from.
            evidence_manager: Source of `Evidence` objects. Expected
                to contain (at least) the evidence referenced by
                whichever case is selected.
            clue_manager: Source of `Clue` objects. Expected to
                contain (at least) the clues referenced by whichever
                case is selected.
            suspect_manager: Source of `Suspect` objects. Expected to
                contain (at least) the suspects referenced by
                whichever case is selected.
            investigator: Display name of whoever is conducting the
                investigation (e.g. a player name). Defaults to
                "Player".
            location_manager: Optional source of `Location` objects.
                When given, the id-based location exploration methods
                (`explore_location_by_id`, `get_available_locations`,
                `get_location_info`, `get_visited_location_ids`)
                become usable. Omitting this (the default) leaves
                those methods unavailable but keeps every existing,
                free-text-based method (`inspect_location`,
                `get_visited_locations`) working exactly as before --
                so existing callers that never pass a
                `LocationManager` are entirely unaffected.

        Raises:
            ValueError: If `investigator` is empty or not a string.
        """
        if not isinstance(investigator, str) or not investigator.strip():
            raise ValueError("investigator must be a non-empty string")

        self.case_manager: CaseManager = case_manager
        self.evidence_manager: EvidenceManager = evidence_manager
        self.clue_manager: ClueManager = clue_manager
        self.suspect_manager: SuspectManager = suspect_manager
        self.location_manager: Optional[LocationManager] = location_manager
        self.investigator: str = investigator

        self.case: Optional[Case] = None
        self.status: str = "not_started"

        self._visited_locations: List[str] = []
        self._current_location_id: Optional[str] = None
        self._examined_suspects: List[str] = []
        self._history: List[Dict[str, Any]] = []

    # -- Internal helpers ---------------------------------------------------

    def _log(self, action: str, details: Optional[Dict[str, Any]] = None) -> None:
        """Append an entry to the investigation's action history."""
        self._history.append(
            {
                "action": action,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "details": dict(details) if details else {},
            }
        )

    def _require_case_selected(self) -> Case:
        if self.case is None:
            raise RuntimeError("No case selected; call select_case() first")
        return self.case

    def _require_active(self) -> Case:
        if self.status != "active" or self.case is None:
            raise RuntimeError(
                "No active investigation; call start_investigation() first"
            )
        return self.case

    @staticmethod
    def _require_nonempty_str(value: Any, field_name: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must be a non-empty string")
        return value

    def _suspect_belongs_to_case(self, case: Case, suspect: Suspect) -> bool:
        return suspect.suspect_id in case.suspects or suspect.name in case.suspects

    # -- Case selection & lifecycle ------------------------------------------

    def select_case(self, case_id: str) -> Case:
        """Choose which case this investigation will focus on.

        Selecting a case does not start it -- call
        `start_investigation()` afterwards (or pass `case_id`
        directly to `start_investigation`).

        Args:
            case_id: Id of a case registered with `case_manager`.

        Returns:
            The selected `Case`.

        Raises:
            ValueError: If `case_id` is empty or not a string.
            RuntimeError: If an investigation is already active
                (end it first before switching cases).
            KeyError: If no case with that id is registered.
        """
        self._require_nonempty_str(case_id, "case_id")
        if self.status == "active":
            raise RuntimeError(
                "Cannot select a new case while an investigation is active; "
                "call end_investigation() first"
            )

        case = self.case_manager.get_case(case_id)
        if case is None:
            raise KeyError(f"No case found with id '{case_id}'")

        self.case = case
        self._log("select_case", {"case_id": case_id})
        return case

    def start_investigation(self, case_id: Optional[str] = None) -> Case:
        """Begin the investigation, optionally selecting a case first.

        Args:
            case_id: If given, selects this case (via `select_case`)
                before starting. If omitted, a case must already have
                been selected.

        Returns:
            The `Case` that is now under investigation.

        Raises:
            ValueError: If `case_id` is given but invalid.
            RuntimeError: If no case is selected, an investigation is
                already active, this investigation has already ended,
                or the underlying case cannot be started (e.g. it was
                already solved/failed).
            KeyError: If `case_id` is given but not found.
        """
        if case_id is not None:
            self.select_case(case_id)

        case = self._require_case_selected()

        if self.status == "active":
            raise RuntimeError("Investigation is already active")
        if self.status == "ended":
            raise RuntimeError(
                "This investigation has already ended; "
                "create a new Investigation to start again"
            )

        case.start()
        self.status = "active"
        self._visited_locations = []
        self._current_location_id = None
        self._examined_suspects = []
        self._log("start_investigation", {"case_id": case.case_id})
        return case

    # -- Locations ------------------------------------------------------------

    def inspect_location(self, location: str) -> Dict[str, Any]:
        """Inspect a location within the current case.

        Inspecting a location does not automatically discover the
        evidence/clues there -- it surfaces what is known to be at
        that location (which items are discovered vs. still hidden)
        so the player can decide what to do next via
        `discover_evidence` / `discover_clue`.

        Args:
            location: Name of the location to inspect (matched
                against `Evidence.location_found` / `Clue.location`).

        Returns:
            A dictionary with the location name, whether this is the
            first visit, and the evidence/clue info available there
            (respecting each item's own discovery-gated `get_info()`).

        Raises:
            ValueError: If `location` is empty or not a string.
            RuntimeError: If no investigation is currently active.
        """
        case = self._require_active()
        self._require_nonempty_str(location, "location")

        first_visit = location not in self._visited_locations
        if first_visit:
            self._visited_locations.append(location)

        evidence_here = [
            evidence.get_info()
            for evidence in self.evidence_manager.get_all_evidence()
            if evidence.evidence_id in case.evidence
            and evidence.location_found == location
        ]
        clues_here = [
            clue.get_info()
            for clue in self.clue_manager.get_all_clues()
            if clue.clue_id in case.clues and clue.location == location
        ]

        self._log(
            "inspect_location",
            {"location": location, "first_visit": first_visit},
        )
        return {
            "location": location,
            "first_visit": first_visit,
            "evidence_here": evidence_here,
            "clues_here": clues_here,
        }

    def get_visited_locations(self) -> List[str]:
        """Return the locations inspected so far, in visit order."""
        return list(self._visited_locations)

    # -- Locations (id-based, via LocationManager) ---------------------------
    #
    # These methods are the id-based counterpart to `inspect_location`/
    # `get_visited_locations` above, built on top of the existing
    # `game.location.Location`/`LocationManager` system. They are
    # entirely additive: nothing above this section changes behavior,
    # and these methods simply aren't usable unless a `location_manager`
    # was supplied at construction time. `Location` itself remains the
    # single authoritative source of visited/visit-count state -- this
    # class never keeps a second, duplicate copy of that; it only
    # tracks the "current location" concept, which `Location`
    # deliberately leaves to its caller (see `game.location` module
    # docstring).

    def _require_location_manager(self) -> LocationManager:
        if self.location_manager is None:
            raise RuntimeError(
                "No LocationManager configured for this investigation"
            )
        return self.location_manager

    def _require_case_location(self, case: Case, location_id: str) -> Location:
        """Validate `location_id` exists and belongs to `case`, returning it."""
        self._require_nonempty_str(location_id, "location_id")
        location_manager = self._require_location_manager()

        if location_id not in case.locations:
            raise KeyError(
                f"Location '{location_id}' does not belong to "
                f"case '{case.case_id}'"
            )

        location = location_manager.get_location(location_id)
        if location is None:
            raise KeyError(f"No location found with id '{location_id}'")

        return location

    def get_available_locations(self) -> List[Location]:
        """Return the `Location` objects registered for the current case.

        Delegates entirely to `LocationManager` -- this method does
        not decide anything about visit state or discovery, it only
        scopes the manager's locations down to the ones the active
        case actually references (via `case.locations`).

        Returns:
            A list of `Location` objects, in the case's declared
            order. Locations referenced by the case but missing from
            `location_manager` (e.g. a data error) are silently
            skipped rather than raising.

        Raises:
            RuntimeError: If no investigation is active, or no
                `LocationManager` was configured for this investigation.
        """
        case = self._require_active()
        location_manager = self._require_location_manager()

        return [
            location
            for location_id in case.locations
            if (location := location_manager.get_location(location_id)) is not None
        ]

    def get_location_info(self, location_id: str) -> Dict[str, Any]:
        """Return a location's info snapshot plus what's available there.

        Unlike `explore_location_by_id`, this does not register a
        visit -- it's a read-only lookup (e.g. for a UI to preview a
        location before committing to explore it).

        Args:
            location_id: Id of the location to look up.

        Returns:
            The location's `get_location_info()` dict, extended with
            `evidence_here`/`clues_here` (the discovery-gated
            `Evidence.get_info()`/`Clue.get_info()` results for the
            evidence/clue ids the location references).

        Raises:
            ValueError: If `location_id` is empty or not a string.
            RuntimeError: If no investigation is active, or no
                `LocationManager` was configured for this investigation.
            KeyError: If the location doesn't exist, or exists but
                doesn't belong to the current case.
        """
        case = self._require_active()
        location = self._require_case_location(case, location_id)

        info = location.get_location_info()
        info["evidence_here"] = [
            evidence.get_info()
            for eid in location.get_available_evidence()
            if eid in case.evidence
            and (evidence := self.evidence_manager.get_evidence(eid)) is not None
        ]
        info["clues_here"] = [
            clue.get_info()
            for cid in location.get_available_clues()
            if cid in case.clues
            and (clue := self.clue_manager.get_clue(cid)) is not None
        ]
        return info

    def explore_location_by_id(self, location_id: str) -> Dict[str, Any]:
        """Explore a location (by id) within the current case.

        Marks the location visited (via `Location.visit()`, the one
        authoritative place visit state lives), sets it as the
        current location, and surfaces the evidence/clue ids
        potentially available there -- exactly like
        `inspect_location()` does for the free-text location model,
        this does *not* automatically discover anything. The caller
        decides what (if anything) to pass to `discover_evidence()` /
        `discover_clue()`.

        Args:
            location_id: Id of the location to explore.

        Returns:
            A dictionary with the location's id/name, whether this is
            the first visit, the running visit count, its connected
            location ids, and the evidence/clue info available there
            (respecting each item's own discovery-gated `get_info()`).

        Raises:
            ValueError: If `location_id` is empty or not a string.
            RuntimeError: If no investigation is active, or no
                `LocationManager` was configured for this investigation.
            KeyError: If the location doesn't exist, or exists but
                doesn't belong to the current case.
        """
        case = self._require_active()
        location = self._require_case_location(case, location_id)

        location.visit()
        first_visit = location.visit_count == 1
        self._current_location_id = location_id

        evidence_here = [
            evidence.get_info()
            for eid in location.get_available_evidence()
            if eid in case.evidence
            and (evidence := self.evidence_manager.get_evidence(eid)) is not None
        ]
        clues_here = [
            clue.get_info()
            for cid in location.get_available_clues()
            if cid in case.clues
            and (clue := self.clue_manager.get_clue(cid)) is not None
        ]

        self._log(
            "explore_location",
            {
                "location_id": location_id,
                "first_visit": first_visit,
                "visit_count": location.visit_count,
            },
        )
        return {
            "location_id": location_id,
            "name": location.name,
            "first_visit": first_visit,
            "visit_count": location.visit_count,
            "connected_locations": location.get_connected_locations(),
            "evidence_here": evidence_here,
            "clues_here": clues_here,
        }

    def get_visited_location_ids(self) -> List[str]:
        """Return the ids of visited locations belonging to the current case.

        Sourced directly from each `Location.is_visited()` (the
        single authoritative source of visit state) rather than a
        second tracked list, so this can never drift out of sync with
        `explore_location_by_id`/`Location.visit()`.

        Returns:
            A list of visited location ids, in the case's declared
            order. Empty if no `LocationManager` is configured, or no
            case is active.
        """
        if self.location_manager is None or self.case is None:
            return []

        return [
            location_id
            for location_id in self.case.locations
            if (location := self.location_manager.get_location(location_id)) is not None
            and location.is_visited()
        ]

    def get_current_location_id(self) -> Optional[str]:
        """Return the id of the location currently being explored, if any."""
        return self._current_location_id

    def get_examined_suspects(self) -> List[str]:
        """Return the ids of suspects examined so far, in examine order."""
        return list(self._examined_suspects)

    def load_state(
        self,
        case: Case,
        status: str = "active",
        visited_locations: Optional[List[str]] = None,
        examined_suspects: Optional[List[str]] = None,
        history: Optional[List[Dict[str, Any]]] = None,
        current_location_id: Optional[str] = None,
    ) -> None:
        """Restore investigation progress from previously saved data.

        Intended for use by `SaveManager`/`GameController` when
        resuming a saved session: rebuilds this investigation's
        internal tracking (visited locations, examined suspects,
        action history) directly, without re-running the original
        gameplay actions. This does not re-validate or replay each
        action -- the caller is responsible for ensuring `case` and
        the associated evidence/clue/suspect managers already reflect
        the discovery state implied by `history`.

        Args:
            case: The `Case` this investigation is resuming.
            status: Investigation status to restore. Must be one of
                `VALID_INVESTIGATION_STATUSES`.
            visited_locations: Previously visited location names.
            examined_suspects: Previously examined suspect ids.
            history: Previously recorded action history entries.
            current_location_id: Previously current location id (see
                `explore_location_by_id`/`get_current_location_id`).
                Note that visited/visit-count state for id-based
                locations is *not* restored here -- that lives on the
                `Location` objects themselves and is restored by
                whoever repopulates `location_manager` (typically
                `SaveManager`), consistent with how evidence/clue
                discovery flags are restored onto `evidence_manager`/
                `clue_manager` rather than here.

        Raises:
            ValueError: If `case` is None/invalid or `status` isn't a
                recognized value.
        """
        if case is None or not hasattr(case, "case_id"):
            raise ValueError("case must be a valid Case instance")
        if status not in VALID_INVESTIGATION_STATUSES:
            raise ValueError(
                f"status must be one of {VALID_INVESTIGATION_STATUSES}, "
                f"got {status!r}"
            )

        self.case = case
        self.status = status
        self._visited_locations = list(visited_locations) if visited_locations else []
        self._examined_suspects = list(examined_suspects) if examined_suspects else []
        self._history = [dict(h) for h in history] if history else []
        self._current_location_id = current_location_id

    # -- Evidence ---------------------------------------------------------

    def discover_evidence(self, evidence_id: str) -> Evidence:
        """Discover a piece of evidence belonging to the current case.

        Args:
            evidence_id: Id of the evidence to discover.

        Returns:
            The now-discovered `Evidence` instance.

        Raises:
            ValueError: If `evidence_id` is empty or not a string.
            RuntimeError: If no investigation is active, or the
                evidence has already been discovered.
            KeyError: If the evidence doesn't exist, or exists but
                doesn't belong to the current case.
        """
        case = self._require_active()
        self._require_nonempty_str(evidence_id, "evidence_id")

        if evidence_id not in case.evidence:
            raise KeyError(
                f"Evidence '{evidence_id}' does not belong to "
                f"case '{case.case_id}'"
            )

        evidence = self.evidence_manager.get_evidence(evidence_id)
        if evidence is None:
            raise KeyError(f"No evidence found with id '{evidence_id}'")

        if evidence.is_discovered():
            raise RuntimeError(
                f"Evidence '{evidence_id}' has already been discovered"
            )

        evidence.discover()
        self._log("discover_evidence", {"evidence_id": evidence_id})
        return evidence

    # -- Clues --------------------------------------------------------------

    def discover_clue(self, clue_id: str) -> Clue:
        """Discover a clue belonging to the current case.

        Args:
            clue_id: Id of the clue to discover.

        Returns:
            The now-discovered `Clue` instance.

        Raises:
            ValueError: If `clue_id` is empty or not a string.
            RuntimeError: If no investigation is active, or the clue
                has already been discovered.
            KeyError: If the clue doesn't exist, or exists but
                doesn't belong to the current case.
        """
        case = self._require_active()
        self._require_nonempty_str(clue_id, "clue_id")

        if clue_id not in case.clues:
            raise KeyError(
                f"Clue '{clue_id}' does not belong to case '{case.case_id}'"
            )

        clue = self.clue_manager.get_clue(clue_id)
        if clue is None:
            raise KeyError(f"No clue found with id '{clue_id}'")

        if clue.is_discovered():
            raise RuntimeError(f"Clue '{clue_id}' has already been discovered")

        clue.discover()
        self._log("discover_clue", {"clue_id": clue_id})
        return clue

    # -- Suspects -------------------------------------------------------------

    def examine_suspect(self, suspect_id: str) -> Suspect:
        """Examine a suspect belonging to the current case.

        Examining a suspect is tracked separately from discovering
        evidence/clues -- a suspect's basic profile is always
        viewable (see `Suspect.get_info`), but each suspect can only
        be logged as "examined" once per investigation to keep
        progress tracking meaningful.

        Args:
            suspect_id: Id of the suspect to examine.

        Returns:
            The examined `Suspect` instance.

        Raises:
            ValueError: If `suspect_id` is empty or not a string.
            RuntimeError: If no investigation is active, or this
                suspect has already been examined in this
                investigation.
            KeyError: If the suspect doesn't exist, or exists but
                doesn't belong to the current case.
        """
        case = self._require_active()
        self._require_nonempty_str(suspect_id, "suspect_id")

        suspect = self.suspect_manager.get_suspect(suspect_id)
        if suspect is None:
            raise KeyError(f"No suspect found with id '{suspect_id}'")

        if not self._suspect_belongs_to_case(case, suspect):
            raise KeyError(
                f"Suspect '{suspect_id}' does not belong to "
                f"case '{case.case_id}'"
            )

        if suspect_id in self._examined_suspects:
            raise RuntimeError(
                f"Suspect '{suspect_id}' has already been examined"
            )

        self._examined_suspects.append(suspect_id)
        self._log("examine_suspect", {"suspect_id": suspect_id})
        return suspect

    def review_statements(self, suspect_id: str) -> List[str]:
        """Review the statements a suspect has made so far.

        Unlike `examine_suspect`, statements may be reviewed
        repeatedly (re-reading testimony is not a "discovery").

        Args:
            suspect_id: Id of the suspect whose statements to review.

        Returns:
            A copy of the suspect's recorded statements, oldest
            first.

        Raises:
            ValueError: If `suspect_id` is empty or not a string.
            RuntimeError: If no investigation is active.
            KeyError: If the suspect doesn't exist, or exists but
                doesn't belong to the current case.
        """
        case = self._require_active()
        self._require_nonempty_str(suspect_id, "suspect_id")

        suspect = self.suspect_manager.get_suspect(suspect_id)
        if suspect is None:
            raise KeyError(f"No suspect found with id '{suspect_id}'")

        if not self._suspect_belongs_to_case(case, suspect):
            raise KeyError(
                f"Suspect '{suspect_id}' does not belong to "
                f"case '{case.case_id}'"
            )

        statements = suspect.get_statements()
        self._log(
            "review_statements",
            {"suspect_id": suspect_id, "statement_count": len(statements)},
        )
        return statements

    # -- Progress & history -----------------------------------------------

    def get_progress(self) -> Dict[str, Any]:
        """Return a snapshot of the investigation's current progress.

        Returns:
            A dictionary summarizing status, the selected case (if
            any), locations visited, and evidence/clue/suspect
            discovery counts. Safe to call in any state -- returns a
            minimal summary if no case has been selected yet.
        """
        if self.case is None:
            return {
                "status": self.status,
                "case_id": None,
                "investigator": self.investigator,
            }

        case = self.case

        total_evidence = len(case.evidence)
        discovered_evidence = sum(
            1
            for eid in case.evidence
            if (evidence := self.evidence_manager.get_evidence(eid)) is not None
            and evidence.is_discovered()
        )

        total_clues = len(case.clues)
        discovered_clues = sum(
            1
            for cid in case.clues
            if (clue := self.clue_manager.get_clue(cid)) is not None
            and clue.is_discovered()
        )

        total_suspects = len(case.suspects)
        examined_suspects = len(self._examined_suspects)

        total_items = total_evidence + total_clues
        discovered_items = discovered_evidence + discovered_clues
        completion_percent = (
            round((discovered_items / total_items) * 100, 1)
            if total_items > 0
            else 0.0
        )

        return {
            "status": self.status,
            "case_id": case.case_id,
            "case_status": case.get_status(),
            "investigator": self.investigator,
            "locations_visited": len(self._visited_locations),
            "evidence_discovered": discovered_evidence,
            "evidence_total": total_evidence,
            "clues_discovered": discovered_clues,
            "clues_total": total_clues,
            "suspects_examined": examined_suspects,
            "suspects_total": total_suspects,
            "completion_percent": completion_percent,
        }

    def get_history(self) -> List[Dict[str, Any]]:
        """Return the full, chronologically ordered action history.

        Each entry records the action name, a UTC ISO-8601 timestamp,
        and action-specific details (e.g. which evidence id was
        discovered). Includes actions like `select_case` that happen
        before the investigation becomes "active".

        Returns:
            A copy of the internal history log (safe to mutate
            without affecting the investigation).
        """
        return [dict(entry) for entry in self._history]

    # -- Ending -------------------------------------------------------------

    def end_investigation(
        self, accused_suspect: Optional[str] = None
    ) -> Dict[str, Any]:
        """End the current investigation.

        Args:
            accused_suspect: If given, the investigation is resolved
                by accusing this suspect (passed through to
                `Case.complete_case`), marking the case "solved" or
                "failed". If omitted, the investigation is simply
                abandoned -- the case's own status is left unchanged
                (it stays "in_progress").

        Returns:
            A dictionary summarizing the outcome: `case_id`,
            `accused_suspect`, whether the accusation was correct
            (`solved`, False if no accusation was made), the case's
            final status, and the investigation's final progress
            snapshot.

        Raises:
            RuntimeError: If no investigation is currently active.
            ValueError: If `accused_suspect` is given but empty/not a
                string.
        """
        case = self._require_active()

        if accused_suspect is not None:
            self._require_nonempty_str(accused_suspect, "accused_suspect")
            solved = case.complete_case(accused_suspect)
        else:
            solved = False

        progress = self.get_progress()
        self.status = "ended"

        outcome = {
            "case_id": case.case_id,
            "accused_suspect": accused_suspect,
            "solved": solved,
            "case_status": case.get_status(),
            "progress": progress,
        }
        self._log("end_investigation", outcome)
        return outcome

    def __repr__(self) -> str:
        case_id = self.case.case_id if self.case is not None else None
        return (
            f"Investigation(case_id={case_id!r}, status={self.status!r}, "
            f"investigator={self.investigator!r})"
        )
