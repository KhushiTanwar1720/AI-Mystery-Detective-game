"""
SaveManager module for AI Mystery Detective.

Defines:
- `SaveManager`: OOP class managing save/load operations for `GameState` using
  versioned JSON format.

Supports:
- save_game()
- load_game()
- save_exists()
- delete_save()
- list_saves()
- get_save_info()

Atomic safe file writes are used to prevent file corruption during save operations.
This module is independent of UI.

Beyond the scalar fields already tracked directly on `GameState`
(score, accuracy, rank, discovered evidence/clue ids, interrogation
history, ...), a few pieces of "current investigation" state actually
live on objects owned elsewhere:

- Whether a specific `Evidence`/`Clue` has been discovered is a flag
  on the `Evidence`/`Clue` object itself (owned by `EvidenceManager`/
  `ClueManager`), not on `GameState`.
- A suspect's alibi, recorded behavior, statements, and suspicion
  level live on the `Suspect` object (owned by `SuspectManager`).
- Visited locations, examined-suspect ids, and the action log live on
  the `Investigation` object.

`SaveManager` does not duplicate any of that business logic -- it only
serializes/deserializes those objects using their own existing
`to_dict()`/`from_dict()` (or, for `Investigation`, its `load_state()`
restore helper). All of this extra context is optional: passing only
a `GameState` still works exactly as before, so existing callers are
unaffected.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from game.achievement import AchievementManager
from game.case import Case, CaseManager
from game.clue import Clue, ClueManager
from game.evidence import Evidence, EvidenceManager
from game.game_state import GameState
from game.investigation import Investigation
from game.location import Location, LocationManager
from game.player import Player
from game.suspect import MAX_SUSPICION_LEVEL, MIN_SUSPICION_LEVEL, Suspect, SuspectManager

CURRENT_SAVE_VERSION = 1


class SaveManager:
    """Manages serialization, storage, loading, and deletion of GameState save files."""

    def __init__(
        self,
        saves_dir: Optional[Union[str, Path]] = None,
        case_manager: Optional[CaseManager] = None,
    ) -> None:
        """Initialize SaveManager.

        Args:
            saves_dir: Directory where save files will be stored. Defaults to
                a 'saves' directory at project root if omitted.
            case_manager: Optional CaseManager used when rebuilding Case objects
                during save loading.
        """
        if saves_dir is None:
            saves_dir = Path(__file__).resolve().parent.parent / "saves"

        self.saves_dir: Path = Path(saves_dir)
        self.case_manager: Optional[CaseManager] = case_manager
        # Directory creation is deferred to save_game() (see below)
        # rather than done eagerly here, so simply constructing a
        # SaveManager -- e.g. the one GameController creates for every
        # session -- doesn't create an on-disk "saves/" folder before
        # the player has actually saved anything.

    def _get_slot_path(self, slot_name: str) -> Path:
        """Sanitize slot_name and return save file Path."""
        if not isinstance(slot_name, str) or not slot_name.strip():
            raise ValueError("slot_name must be a non-empty string")

        clean_name = "".join(c for c in slot_name if c.isalnum() or c in ("_", "-")).strip()
        if not clean_name:
            clean_name = "slot_1"

        return self.saves_dir / f"{clean_name}.json"

    def _read_payload(self, slot_name: str) -> Optional[Dict[str, Any]]:
        """Read and lightly validate the raw JSON payload for a save slot.

        Returns:
            The parsed payload dict if it exists and has the minimal
            expected shape (a dict with "version" and "game_state"),
            otherwise None. Never raises -- corrupt/missing files are
            treated as "no save".
        """
        if not self.save_exists(slot_name):
            return None

        try:
            target_path = self._get_slot_path(slot_name)
            with open(target_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception:
            return None

        if not isinstance(payload, dict):
            return None
        if "version" not in payload or "game_state" not in payload:
            return None
        if not isinstance(payload["game_state"], dict):
            return None

        return payload

    # -- Saving ---------------------------------------------------------------

    def save_game(
        self,
        game_state: GameState,
        slot_name: str = "slot_1",
        evidence_manager: Optional[EvidenceManager] = None,
        clue_manager: Optional[ClueManager] = None,
        suspect_manager: Optional[SuspectManager] = None,
        investigation: Optional[Investigation] = None,
        achievement_manager: Optional[AchievementManager] = None,
        location_manager: Optional[LocationManager] = None,
    ) -> bool:
        """Save a GameState instance to a versioned JSON save file atomically.

        Args:
            game_state: GameState instance to persist.
            slot_name: Slot identifier (e.g. "slot_1", "save_001").
            evidence_manager: Optional. When given (together with an
                active `game_state.case`), each piece of evidence
                belonging to the case is persisted via its own
                `to_dict()`, capturing its `discovered` flag -- not
                just the id list already tracked on `GameState`.
            clue_manager: Optional. Same idea as `evidence_manager`,
                for the case's clues.
            suspect_manager: Optional. When given, every suspect
                belonging to the case is persisted via its own
                `to_dict()`, capturing alibi/behavior/statements/
                suspicion level.
            investigation: Optional. When given, the investigation's
                visited locations, examined-suspect ids, status,
                current (id-based) location, and action history are
                persisted so a reload can restore them via
                `Investigation.load_state()`.
            achievement_manager: Optional. When given, every
                registered achievement's definition and unlock
                state/timestamp is persisted via its own `to_dict()`,
                so a reload can restore unlocked achievements exactly.
                Omitting this (as old callers do) simply leaves
                achievement data out of the save -- fully backward
                compatible.
            location_manager: Optional. When given (together with an
                active `game_state.case`), each id-based `Location`
                belonging to the case is persisted via its own
                `to_dict()`, capturing its `visited`/`visit_count`
                state -- mirroring how evidence/clue discovery flags
                are captured. Omitting this leaves location visit
                state out of the save -- fully backward compatible.

        Returns:
            True if saving succeeded, False otherwise.
        """
        if game_state is None or not hasattr(game_state, "to_dict"):
            return False

        try:
            target_path = self._get_slot_path(slot_name)
            self.saves_dir.mkdir(parents=True, exist_ok=True)

            state_dict = game_state.to_dict()

            # Enrich state_dict with full Player & Case data if present.
            # Player is serialized field-by-field (rather than relying
            # on a Player.to_dict(), which doesn't exist) so that
            # in-progress case tracking (current_case, collected
            # evidence/clues) round-trips too, not just cumulative
            # totals like cases_solved/investigation_score.
            if game_state.player:
                player = game_state.player
                state_dict["player"] = {
                    "player_id": player.player_id,
                    "name": player.name,
                    "cases_solved": player.cases_solved,
                    "current_case": player.current_case,
                    "collected_evidence": list(player.collected_evidence),
                    "discovered_clues": list(player.discovered_clues),
                    "investigation_score": player.investigation_score,
                }

            if game_state.case and hasattr(game_state.case, "to_dict"):
                state_dict["case_data"] = game_state.case.to_dict()

            payload: Dict[str, Any] = {
                "version": CURRENT_SAVE_VERSION,
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "slot_name": slot_name,
                "game_state": state_dict,
            }

            case = game_state.case

            if evidence_manager is not None and case is not None:
                payload["evidence_data"] = [
                    evidence.to_dict()
                    for eid in case.evidence
                    if (evidence := evidence_manager.get_evidence(eid)) is not None
                ]

            if clue_manager is not None and case is not None:
                payload["clue_data"] = [
                    clue.to_dict()
                    for cid in case.clues
                    if (clue := clue_manager.get_clue(cid)) is not None
                ]

            if suspect_manager is not None and case is not None:
                payload["suspect_data"] = [
                    suspect.to_dict()
                    for suspect in suspect_manager.get_suspects_for_case(case)
                ]

            if investigation is not None:
                payload["investigation_state"] = {
                    "status": investigation.status,
                    "visited_locations": investigation.get_visited_locations(),
                    "examined_suspects": investigation.get_examined_suspects(),
                    "history": investigation.get_history(),
                    "current_location_id": investigation.get_current_location_id(),
                }

            if achievement_manager is not None:
                payload["achievement_data"] = achievement_manager.to_dict()

            if location_manager is not None and case is not None:
                payload["location_data"] = [
                    location.to_dict()
                    for location_id in case.locations
                    if (location := location_manager.get_location(location_id)) is not None
                ]

            # Atomic file write using a temporary file
            temp_path = target_path.with_suffix(".tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)

            temp_path.replace(target_path)
            return True
        except Exception:
            return False

    # -- Loading ----------------------------------------------------------------

    def load_game(
        self,
        slot_name: str = "slot_1",
        case_manager: Optional[CaseManager] = None,
        evidence_manager: Optional[EvidenceManager] = None,
        clue_manager: Optional[ClueManager] = None,
        suspect_manager: Optional[SuspectManager] = None,
        location_manager: Optional[LocationManager] = None,
    ) -> Optional[GameState]:
        """Load and reconstruct a GameState from a JSON save file safely.

        Args:
            slot_name: Slot identifier.
            case_manager: Optional CaseManager to resolve cases. Defaults to
                self.case_manager if set.
            evidence_manager: Optional. When given, this manager's
                `Evidence` objects are updated in place (or added, if
                missing) with the saved `discovered` flag and related
                data, restoring evidence discovery state that
                `GameState` alone doesn't own.
            clue_manager: Optional. Same idea as `evidence_manager`,
                for clues.
            suspect_manager: Optional. When given, this manager's
                `Suspect` objects are updated in place (or added, if
                missing) with saved alibi/behavior/statements/
                suspicion level.
            location_manager: Optional. When given, this manager's
                `Location` objects are updated in place (or added, if
                missing) with saved `visited`/`visit_count` state,
                restoring id-based location progress that `GameState`
                alone doesn't own.

        Returns:
            Reconstructed GameState instance, or None if file is missing/corrupt.
        """
        payload = self._read_payload(slot_name)
        if payload is None:
            return None

        version = payload.get("version")
        if not isinstance(version, int) or isinstance(version, bool) or version > CURRENT_SAVE_VERSION:
            # Unknown/newer save format than this build understands --
            # refuse to guess at how to reconstruct it rather than
            # risk silently mis-loading state.
            return None

        try:
            state_dict = payload["game_state"]

            # Reconstruct Player
            player_data = state_dict.get("player")
            if isinstance(player_data, dict) and "player_id" in player_data:
                player = Player(
                    player_id=player_data["player_id"],
                    name=player_data.get("name", "Detective"),
                )
                player.cases_solved = int(player_data.get("cases_solved", 0))
                player.investigation_score = int(player_data.get("investigation_score", 0))
                player.current_case = player_data.get("current_case")
                player.collected_evidence = [
                    e for e in player_data.get("collected_evidence", []) if isinstance(e, str)
                ]
                player.discovered_clues = [
                    c for c in player_data.get("discovered_clues", []) if isinstance(c, str)
                ]
            elif state_dict.get("player_id"):
                player = Player(
                    player_id=state_dict["player_id"],
                    name=state_dict.get("player_name", "Detective"),
                )
            else:
                player = Player(player_id="player_default", name="Detective")

            game_state = GameState(player=player)

            # Reconstruct Case
            effective_cm = case_manager or self.case_manager
            case_obj: Optional[Case] = None

            case_data = state_dict.get("case_data")
            if isinstance(case_data, dict):
                try:
                    case_obj = Case.from_dict(case_data)
                except Exception:
                    case_obj = None

            if case_obj is None and state_dict.get("case_id") and effective_cm:
                case_obj = effective_cm.get_case(state_dict["case_id"])

            if case_obj:
                game_state.case = case_obj

            # Restore evidence/clue discovery flags and suspect
            # interrogation state onto the caller's own managers, if
            # provided. GameState itself only tracks *ids*
            # (discovered_evidence/discovered_clues below) -- the
            # actual Evidence/Clue/Suspect objects are owned by these
            # managers, so restoring their state is what makes a
            # reloaded game behave identically to the original.
            if evidence_manager is not None:
                for item in payload.get("evidence_data", []) or []:
                    if isinstance(item, dict):
                        self._restore_evidence(evidence_manager, item)

            if clue_manager is not None:
                for item in payload.get("clue_data", []) or []:
                    if isinstance(item, dict):
                        self._restore_clue(clue_manager, item)

            if suspect_manager is not None:
                for item in payload.get("suspect_data", []) or []:
                    if isinstance(item, dict):
                        self._restore_suspect(suspect_manager, item)

            if location_manager is not None:
                for item in payload.get("location_data", []) or []:
                    if isinstance(item, dict):
                        self._restore_location(location_manager, item)

            # Reconstruct remaining GameState attributes
            game_state.status = str(state_dict.get("status", "not_started"))
            game_state.current_suspect_id = state_dict.get("current_suspect_id")

            for eid in state_dict.get("discovered_evidence", []):
                if isinstance(eid, str) and eid.strip():
                    game_state.add_discovered_evidence(eid)

            for cid in state_dict.get("discovered_clues", []):
                if isinstance(cid, str) and cid.strip():
                    game_state.add_discovered_clue(cid)

            for hist in state_dict.get("interrogation_history", []):
                if isinstance(hist, dict):
                    game_state.record_interrogation(hist)

            game_state.hints_used = max(0, int(state_dict.get("hints_used", 0)))
            game_state.unnecessary_actions = max(0, int(state_dict.get("unnecessary_actions", 0)))

            score = max(0, int(state_dict.get("score", 0)))
            accuracy = max(0.0, min(100.0, float(state_dict.get("accuracy", 0.0))))
            rank = str(state_dict.get("rank", "Detective Rookie"))
            game_state.update_score(score=score, accuracy=accuracy, rank=rank)

            if isinstance(state_dict.get("outcome"), dict):
                game_state.outcome = state_dict["outcome"]

            return game_state
        except Exception:
            return None

    def load_investigation_state(self, slot_name: str = "slot_1") -> Optional[Dict[str, Any]]:
        """Return the raw saved investigation-progress data for a slot, if any.

        This is a companion to `load_game()`: rebuilding a live
        `Investigation` object needs the same `CaseManager`/
        `EvidenceManager`/`ClueManager`/`SuspectManager` instances the
        rest of the session uses, which `SaveManager` intentionally
        doesn't own. Callers (typically `GameController`) use this
        data together with `Investigation.load_state()` to restore
        visited locations, examined suspects, and action history.

        Args:
            slot_name: Slot identifier.

        Returns:
            A dict with "status", "visited_locations",
            "examined_suspects", "history", and "current_location_id"
            keys, or None if the slot doesn't exist, is corrupt, or
            was saved without investigation context (e.g.
            `save_game()` was called without the `investigation`
            argument).
        """
        payload = self._read_payload(slot_name)
        if payload is None:
            return None

        data = payload.get("investigation_state")
        if not isinstance(data, dict):
            return None

        current_location_id = data.get("current_location_id")
        if not isinstance(current_location_id, str) or not current_location_id.strip():
            current_location_id = None

        return {
            "status": str(data.get("status", "active")),
            "visited_locations": [
                loc for loc in data.get("visited_locations", []) if isinstance(loc, str)
            ],
            "examined_suspects": [
                sid for sid in data.get("examined_suspects", []) if isinstance(sid, str)
            ],
            "history": [h for h in data.get("history", []) if isinstance(h, dict)],
            "current_location_id": current_location_id,
        }

    def load_achievement_state(self, slot_name: str = "slot_1") -> Optional[Dict[str, Any]]:
        """Return the raw saved achievement data for a slot, if any.

        Companion to `load_game()`, mirroring `load_investigation_state()`:
        rebuilding an `AchievementManager` needs its own
        `AchievementManager.from_dict()` restore step, which
        `SaveManager` intentionally doesn't perform itself (so it
        never has to import achievement *unlock logic*, only pass the
        raw dict through).

        Args:
            slot_name: Slot identifier.

        Returns:
            The raw `"achievement_data"` dict (suitable for
            `AchievementManager.from_dict()`), or None if the slot
            doesn't exist, is corrupt, or was saved without
            achievement context (e.g. an older save, or `save_game()`
            called without the `achievement_manager` argument).
        """
        payload = self._read_payload(slot_name)
        if payload is None:
            return None

        data = payload.get("achievement_data")
        if not isinstance(data, dict):
            return None

        return data

    # -- Restore helpers (used internally by load_game) ------------------------

    @staticmethod
    def _restore_evidence(evidence_manager: EvidenceManager, data: Dict[str, Any]) -> None:
        """Apply saved evidence data onto `evidence_manager`, in place if possible."""
        evidence_id = data.get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id.strip():
            return

        existing = evidence_manager.get_evidence(evidence_id)
        if existing is not None:
            existing.discovered = bool(data.get("discovered", existing.discovered))
            existing.importance = data.get("importance", existing.importance)
            for suspect in data.get("related_suspects", []) or []:
                if isinstance(suspect, str) and suspect not in existing.related_suspects:
                    existing.related_suspects.append(suspect)
            return

        try:
            evidence_manager.add_evidence(Evidence.from_dict(data))
        except Exception:
            pass

    @staticmethod
    def _restore_clue(clue_manager: ClueManager, data: Dict[str, Any]) -> None:
        """Apply saved clue data onto `clue_manager`, in place if possible."""
        clue_id = data.get("clue_id")
        if not isinstance(clue_id, str) or not clue_id.strip():
            return

        existing = clue_manager.get_clue(clue_id)
        if existing is not None:
            existing.discovered = bool(data.get("discovered", existing.discovered))
            existing.importance = data.get("importance", existing.importance)
            for evidence_id in data.get("related_evidence", []) or []:
                if isinstance(evidence_id, str) and evidence_id not in existing.related_evidence:
                    existing.related_evidence.append(evidence_id)
            for suspect in data.get("related_suspects", []) or []:
                if isinstance(suspect, str) and suspect not in existing.related_suspects:
                    existing.related_suspects.append(suspect)
            return

        try:
            clue_manager.add_clue(Clue.from_dict(data))
        except Exception:
            pass

    @staticmethod
    def _restore_suspect(suspect_manager: SuspectManager, data: Dict[str, Any]) -> None:
        """Apply saved suspect data onto `suspect_manager`, in place if possible."""
        suspect_id = data.get("suspect_id")
        if not isinstance(suspect_id, str) or not suspect_id.strip():
            return

        existing = suspect_manager.get_suspect(suspect_id)
        if existing is not None:
            existing.alibi = data.get("alibi", existing.alibi)
            existing.behavior = [b for b in data.get("behavior", existing.behavior) if isinstance(b, str)]
            existing.statements = [
                s for s in data.get("statements", existing.statements) if isinstance(s, str)
            ]
            try:
                level = int(data.get("suspicion_level", existing.suspicion_level))
            except (TypeError, ValueError):
                level = existing.suspicion_level
            existing.suspicion_level = max(MIN_SUSPICION_LEVEL, min(MAX_SUSPICION_LEVEL, level))
            return

        try:
            suspect_manager.add_suspect(Suspect.from_dict(data))
        except Exception:
            pass

    @staticmethod
    def _restore_location(location_manager: LocationManager, data: Dict[str, Any]) -> None:
        """Apply saved location data onto `location_manager`, in place if possible."""
        location_id = data.get("location_id")
        if not isinstance(location_id, str) or not location_id.strip():
            return

        existing = location_manager.get_location(location_id)
        if existing is not None:
            existing.visited = bool(data.get("visited", existing.visited))
            try:
                visit_count = int(data.get("visit_count", existing.visit_count))
            except (TypeError, ValueError):
                visit_count = existing.visit_count
            existing.visit_count = max(0, visit_count)
            return

        try:
            location_manager.add_location(Location.from_dict(data))
        except Exception:
            pass

    # -- Slot management --------------------------------------------------------

    def save_exists(self, slot_name: str = "slot_1") -> bool:
        """Return True if a save file exists for slot_name."""
        try:
            target_path = self._get_slot_path(slot_name)
            return target_path.exists() and target_path.is_file()
        except Exception:
            return False

    def delete_save(self, slot_name: str = "slot_1") -> bool:
        """Delete save file for slot_name if it exists.

        Returns:
            True if save existed and was deleted, False otherwise.
        """
        try:
            if not self.save_exists(slot_name):
                return False
            target_path = self._get_slot_path(slot_name)
            target_path.unlink()
            return True
        except Exception:
            return False

    def list_saves(self) -> List[Dict[str, Any]]:
        """List all valid save files found in saves_dir with metadata summary."""
        if not self.saves_dir.exists():
            return []

        saves: List[Dict[str, Any]] = []
        for file_path in sorted(self.saves_dir.glob("*.json")):
            slot_name = file_path.stem
            info = self.get_save_info(slot_name)
            if info:
                saves.append(info)

        return saves

    def get_save_info(self, slot_name: str = "slot_1") -> Optional[Dict[str, Any]]:
        """Read and return header metadata summary of a save file without full reconstruction."""
        payload = self._read_payload(slot_name)
        if payload is None:
            return None

        state = payload.get("game_state", {})
        return {
            "slot_name": payload.get("slot_name", slot_name),
            "version": payload.get("version", 1),
            "saved_at": payload.get("saved_at"),
            "player_name": state.get("player", {}).get("name") or state.get("player_name", "Detective"),
            "case_id": state.get("case_id"),
            "status": state.get("status"),
            "score": state.get("score", 0),
            "accuracy": state.get("accuracy", 0.0),
            "rank": state.get("rank", "Detective Rookie"),
        }
