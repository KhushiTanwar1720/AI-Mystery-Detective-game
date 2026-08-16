"""
Game controller for AI Mystery Detective.

Defines the `GameController` class, the single orchestrator that
wires the existing foundation modules (`Case`/`CaseManager`,
`Player`, `Suspect`/`SuspectManager`, `Evidence`/`EvidenceManager`,
`Clue`/`ClueManager`) together with the existing higher-level modules
(`Investigation`, `Interrogation`, `AIAnalyzer`) into one coherent,
playable backend flow:

    Case -> Player -> Investigation -> Evidence/Clues -> Suspects
         -> Interrogation -> AI Analyzer -> Investigation Result

`GameController` does not implement any new gameplay rules itself --
every rule (validation, discovery gating, scoring, suspicion, etc.)
already lives in the modules it coordinates. Its only job is data
plumbing: loading a case's associated suspects/evidence/clues,
constructing `Investigation`/`Interrogation`/`AIAnalyzer` objects with
the right inputs, and forwarding results from one stage to the next
so nothing is left as an isolated, unreachable local object.

This module is intentionally UI-free (no `input()`/`print()`), so a
future `ui` layer (CLI, GUI, or web) can drive the exact same
`GameController` API that `game.app.App` uses for its own scripted
playthrough.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from game.achievement import Achievement, AchievementManager
from game.ai_analyzer import AIAnalyzer, AnalysisResult
from game.case import Case, CaseManager
from game.clue import Clue, ClueManager
from game.evidence import Evidence, EvidenceManager
from game.interrogation import Interrogation, Question, Statement
from game.investigation import Investigation
from game.location import Location, LocationManager
from game.player import Player
from game.save_manager import SaveManager
from game.scoring import ScoreManager
from game.game_state import GameState
from game.suspect import Suspect, SuspectManager


class GameController:
    """Top-level orchestrator connecting all game modules.

    A `GameController` owns one set of `CaseManager` /
    `EvidenceManager` / `ClueManager` / `SuspectManager` instances, a
    `Player`, and (as the game progresses) the active `Investigation`,
    `Interrogation`, and `AIAnalyzer` for the current session. It does
    not duplicate any logic already implemented in those classes --
    it only sequences calls to them and passes results along.
    """

    def __init__(
        self,
        player_id: str,
        player_name: str,
        cases_dir: Optional[str] = None,
        saves_dir: Optional[str] = None,
    ) -> None:
        """Create a new game session.

        Args:
            player_id: Unique identifier for the player.
            player_name: Display name for the player.
            cases_dir: Optional override for the directory `Case`
                JSON files (and the `suspects/`, `evidence/`, and
                `clues/` subfolders) are loaded from. Defaults to the
                project's `cases/` directory (see `CaseManager`).
            saves_dir: Optional override for the directory save files
                are written to/read from. Defaults to the project's
                `saves/` directory (see `SaveManager`).
        """
        self.case_manager: CaseManager = CaseManager(cases_dir)
        self.evidence_manager: EvidenceManager = EvidenceManager()
        self.clue_manager: ClueManager = ClueManager()
        self.suspect_manager: SuspectManager = SuspectManager()
        self.location_manager: LocationManager = LocationManager()
        self.player: Player = Player(player_id, player_name)
        self.score_manager: ScoreManager = ScoreManager()
        self.game_state: GameState = GameState(self.player)
        self.game_state.start_game(self.player)
        self.save_manager: SaveManager = SaveManager(
            saves_dir=saves_dir, case_manager=self.case_manager
        )
        self.achievement_manager: AchievementManager = AchievementManager()

        self.case: Optional[Case] = None
        self.investigation: Optional[Investigation] = None
        self.interrogation: Optional[Interrogation] = None
        self.ai_analyzer: Optional[AIAnalyzer] = None
        self._hints_used: int = 0
        self._unnecessary_actions: int = 0
        self._last_interrogation_outcome: Optional[Dict[str, Any]] = None

    # -- Stage 1-2: Case -----------------------------------------------------

    def load_case(self, case_id: str) -> Case:
        """Load a `Case` plus its associated suspects/evidence/clues.

        Loads every case in `cases_dir` (if not already loaded), then
        loads the suspect/evidence/clue JSON files associated with
        `case_id` -- by convention `cases/suspects/<case_id>_suspects.json`,
        `cases/evidence/<case_id>_evidence.json`, and
        `cases/clues/<case_id>_clues.json` -- into their respective
        managers.

        Newly loaded evidence and clue ids are also registered onto
        the `Case` itself (via `Case.add_evidence` / `Case.add_clue`),
        since case JSON files only list suspects by name and leave
        `evidence`/`clues` empty for per-case data files to fill in.
        This is what actually connects `Case` to the evidence/clue
        data `Investigation` needs -- without it, `case.evidence` and
        `case.clues` stay empty and nothing could ever be discovered.

        Args:
            case_id: Id of the case to load (matches a `.json` file's
                `case_id` field in `cases_dir`).

        Returns:
            The loaded `Case`.

        Raises:
            KeyError: If no case with that id is found.
        """
        if not self.case_manager.get_all_cases():
            self.case_manager.load_all_cases()

        case = self.case_manager.get_case(case_id)
        if case is None:
            raise KeyError(f"No case found with id '{case_id}'")

        self._load_case_data(case)
        self.case = case
        return case

    def _load_case_data(self, case: Case) -> None:
        """Load and link the suspect/evidence/clue/location files for `case`."""
        base_dir = self.case_manager.cases_dir

        suspects_file = base_dir / "suspects" / f"{case.case_id}_suspects.json"
        if suspects_file.exists():
            self.suspect_manager.load_suspect_from_file(suspects_file)

        evidence_file = base_dir / "evidence" / f"{case.case_id}_evidence.json"
        if evidence_file.exists():
            for evidence in self.evidence_manager.load_evidence_from_file(evidence_file):
                case.add_evidence(evidence.evidence_id)

        clues_file = base_dir / "clues" / f"{case.case_id}_clues.json"
        if clues_file.exists():
            for clue in self.clue_manager.load_clue_from_file(clues_file):
                case.add_clue(clue.clue_id)

        locations_file = base_dir / "locations" / f"{case.case_id}_locations.json"
        if locations_file.exists():
            for location in self.location_manager.load_location_from_file(locations_file):
                case.add_location(location.location_id)

    def get_case_suspects(self) -> List[Suspect]:
        """Return the `Suspect` objects registered for the loaded case."""
        case = self._require_case()
        return self.suspect_manager.get_suspects_for_case(case)

    # -- Stage 3-4: Player & Investigation ------------------------------------

    def start_investigation(self, case_id: Optional[str] = None) -> Investigation:
        """Start the player's case and begin an `Investigation`.

        Args:
            case_id: If given, loads this case first (via
                `load_case`). If omitted, a case must already be
                loaded.

        Returns:
            The now-active `Investigation`.

        Raises:
            RuntimeError: If no case is loaded.
            KeyError: If `case_id` is given but not found.
        """
        if case_id is not None:
            self.load_case(case_id)

        case = self._require_case()

        self.player.start_case(case.case_id)
        self.investigation = Investigation(
            case_manager=self.case_manager,
            evidence_manager=self.evidence_manager,
            clue_manager=self.clue_manager,
            suspect_manager=self.suspect_manager,
            investigator=self.player.name,
            location_manager=self.location_manager,
        )
        self.investigation.start_investigation(case.case_id)
        self.game_state.start_case(case, self.investigation)
        return self.investigation

    # -- Stage 5: Evidence / Clues --------------------------------------------

    def explore_location(self, location: str) -> Dict[str, Any]:
        """Inspect a location, surfacing evidence/clues known to be there."""
        investigation = self._require_investigation()
        return investigation.inspect_location(location)

    def get_case_locations(self) -> List[str]:
        """Return every location referenced by the loaded case's
        evidence and clues, so a caller can drive `explore_location`
        without needing to know the case's geography in advance.
        """
        case = self._require_case()
        locations = {
            e.location_found
            for e in self.evidence_manager.get_all_evidence()
            if e.evidence_id in case.evidence
        }
        locations.update(
            c.location
            for c in self.clue_manager.get_all_clues()
            if c.clue_id in case.clues
        )
        return sorted(locations)

    # -- Stage 5b: Locations (id-based, via LocationManager) ------------------
    #
    # These are the id-based counterpart to `explore_location`/
    # `get_case_locations` above -- built on the structured
    # `game.location.Location`/`LocationManager` system (locations with
    # ids, connections, and referenced evidence/clue ids) rather than
    # free-text location name matching. GameController does not
    # implement any location business logic itself; every method here
    # is a thin delegation to `Investigation`'s own id-based location
    # methods, which in turn delegate to `LocationManager`/`Location`
    # (the single authoritative source of visit state). Naming is kept
    # distinct from the free-text methods above (matching how
    # `Investigation` itself distinguishes them) so neither model's
    # behavior changes for existing callers.

    def get_available_locations(self) -> List[Location]:
        """Return the `Location` objects registered for the current case."""
        investigation = self._require_investigation()
        return investigation.get_available_locations()

    def explore_location_by_id(self, location_id: str) -> Dict[str, Any]:
        """Explore a location (by id), marking it visited and surfacing
        the evidence/clue ids potentially available there.
        """
        investigation = self._require_investigation()
        return investigation.explore_location_by_id(location_id)

    def get_location_info(self, location_id: str) -> Dict[str, Any]:
        """Return a location's info snapshot plus what's available there,
        without registering a visit.
        """
        investigation = self._require_investigation()
        return investigation.get_location_info(location_id)

    def get_visited_location_ids(self) -> List[str]:
        """Return the ids of visited locations belonging to the current case."""
        investigation = self._require_investigation()
        return investigation.get_visited_location_ids()

    def get_current_location_id(self) -> Optional[str]:
        """Return the id of the location currently being explored, if any."""
        investigation = self._require_investigation()
        return investigation.get_current_location_id()

    def discover_evidence(self, evidence_id: str) -> Evidence:
        """Discover a piece of evidence and record it on the player."""
        investigation = self._require_investigation()
        evidence = investigation.discover_evidence(evidence_id)
        self.player.add_evidence(evidence_id)
        self.game_state.add_discovered_evidence(evidence_id)
        self.achievement_manager.check_achievements(self._build_achievement_stats())
        return evidence

    def discover_clue(self, clue_id: str) -> Clue:
        """Discover a clue and record it on the player."""
        investigation = self._require_investigation()
        clue = investigation.discover_clue(clue_id)
        self.player.add_clue(clue_id)
        self.game_state.add_discovered_clue(clue_id)
        self.achievement_manager.check_achievements(self._build_achievement_stats())
        return clue

    # -- Stage 6: Suspects -----------------------------------------------------

    def examine_suspect(self, suspect_id: str) -> Suspect:
        """Examine a suspect belonging to the current case."""
        investigation = self._require_investigation()
        suspect = investigation.examine_suspect(suspect_id)
        self.game_state.set_current_suspect(suspect_id)
        return suspect

    # -- Stage 7: Interrogation ------------------------------------------------

    def start_interrogation(self, suspect_id: str) -> Interrogation:
        """Begin an `Interrogation` session with a suspect.

        Uses the same `SuspectManager` as the active `Investigation`,
        so statements recorded here are immediately visible to it
        (and to any later `AIAnalyzer` run over the same suspects).

        Args:
            suspect_id: Id of the suspect to interrogate.

        Returns:
            The now-active `Interrogation`.
        """
        self.interrogation = Interrogation(
            suspect_manager=self.suspect_manager,
            interrogator=self.player.name,
        )
        self.interrogation.start_interrogation(suspect_id)
        self.game_state.set_current_suspect(suspect_id)
        self.game_state.interrogation = self.interrogation
        return self.interrogation

    def ask_question(self, text: str, category: str = "general") -> Question:
        """Pose a question to the suspect currently being interrogated."""
        interrogation = self._require_interrogation()
        return interrogation.ask_question(text, category)

    def record_answer(self, question_id: str, answer: str) -> Statement:
        """Record the suspect's answer to a previously asked question."""
        interrogation = self._require_interrogation()
        return interrogation.record_answer(question_id, answer)

    def end_interrogation(self) -> Dict[str, Any]:
        """End the current interrogation session and return its summary."""
        interrogation = self._require_interrogation()
        outcome = interrogation.end_interrogation()
        self._last_interrogation_outcome = outcome
        self.game_state.record_interrogation(outcome)
        return outcome

    # -- Stage 8: AI Analyzer --------------------------------------------------

    def run_ai_analysis(self, include_hints: bool = True) -> AnalysisResult:
        """Run the `AIAnalyzer` over everything gathered so far.

        Collects the current case info (via `Case.get_info()`, which
        never includes the solution), the case's suspects, its
        discovered-aware evidence/clue objects, any statements
        recorded during interrogation, and the combined
        investigation/interrogation action history -- then feeds all
        of it into a fresh `AIAnalyzer` and returns a full
        investigation summary.

        Returns:
            The `AnalysisResult` from `AIAnalyzer.generate_investigation_summary`.

        Raises:
            RuntimeError: If no case has been loaded yet.
        """
        case = self._require_case()

        if include_hints:
            self._hints_used = self.game_state.record_hint()

        suspects = self.suspect_manager.get_suspects_for_case(case)
        evidence = [
            e
            for eid in case.evidence
            if (e := self.evidence_manager.get_evidence(eid)) is not None
        ]
        clues = [
            c
            for cid in case.clues
            if (c := self.clue_manager.get_clue(cid)) is not None
        ]

        statements: Optional[Dict[str, List[Dict[str, str]]]] = None
        history: List[Dict[str, Any]] = []
        if self.investigation is not None:
            history.extend(self.investigation.get_history())
        if self.interrogation is not None:
            history.extend(self.interrogation.get_history())
            statements = {}
            for statement in self.interrogation.get_statements():
                statements.setdefault(statement.suspect_id, []).append(
                    {"question": statement.question_text, "answer": statement.answer}
                )

        self.ai_analyzer = AIAnalyzer(
            case_info=case.get_info(),
            suspects=suspects,
            evidence=evidence,
            clues=clues,
            statements=statements,
            investigation_history=history,
        )
        return self.ai_analyzer.generate_investigation_summary(include_hints=include_hints)

    # -- Stage 9: Investigation Result ------------------------------------------

    def conclude_case(self, accused_suspect: str) -> Dict[str, Any]:
        """End the investigation with a final accusation and compute score/rank.

        Args:
            accused_suspect: Name/id of the suspect being accused
                (compared against `Case.correct_suspect`).

        Returns:
            The outcome dictionary from `Investigation.end_investigation`
            enriched with `score_info`.

        Raises:
            RuntimeError: If no investigation is active.
        """
        investigation = self._require_investigation()
        case = self._require_case()
        outcome = investigation.end_investigation(accused_suspect=accused_suspect)

        solved = outcome["solved"]

        discovered_evidence = [
            e.get_info()
            for eid in case.evidence
            if (e := self.evidence_manager.get_evidence(eid)) is not None and e.is_discovered()
        ]

        discovered_clues = [
            c.get_info()
            for cid in case.clues
            if (c := self.clue_manager.get_clue(cid)) is not None and c.is_discovered()
        ]

        contradictions_count = 0
        if self._last_interrogation_outcome:
            contradictions_count = len(self._last_interrogation_outcome.get("contradictions", []))

        action_count = len(investigation.get_history())

        final_score = self.score_manager.calculate_score(
            solved=solved,
            evidence_list=discovered_evidence,
            clues_list=discovered_clues,
            contradictions_found=contradictions_count,
            unnecessary_actions=self._unnecessary_actions,
            action_count=action_count,
            hints_used=self._hints_used,
            difficulty=case.difficulty,
            total_evidence_count=len(case.evidence),
            total_clues_count=len(case.clues),
        )

        self.player.update_score(final_score)
        self.player.complete_case()

        self.game_state.update_score(
            score=final_score,
            accuracy=self.score_manager.current_accuracy,
            rank=self.score_manager.get_rank(),
        )

        outcome["score_info"] = self.score_manager.get_score_summary()
        self.game_state.end_case(outcome)

        newly_unlocked = self.achievement_manager.check_achievements(
            self._build_achievement_stats(solved=solved, action_count=action_count)
        )
        outcome["achievements_unlocked"] = [a.achievement_id for a in newly_unlocked]

        return outcome

    # -- Stage 10: Save / Load --------------------------------------------------

    def save_game(self, slot_name: str = "slot_1") -> bool:
        """Save the current session to a named slot.

        Delegates the actual file I/O to `self.save_manager`, but
        supplies it with everything a reload needs to reproduce this
        exact session: the current `GameState` (score, discovered
        ids, interrogation history, ...), the `Case` itself, and the
        live `evidence_manager` / `clue_manager` / `suspect_manager` /
        `investigation` objects so per-item discovery flags and
        suspect interrogation state are captured too -- not just the
        summary counts already on `GameState`.

        Args:
            slot_name: Slot identifier (e.g. "slot_1", "save_001").

        Returns:
            True if saving succeeded, False otherwise (e.g. no case
            has been loaded yet, or the save file could not be
            written).
        """
        if self.case is None:
            return False

        return self.save_manager.save_game(
            self.game_state,
            slot_name=slot_name,
            evidence_manager=self.evidence_manager,
            clue_manager=self.clue_manager,
            suspect_manager=self.suspect_manager,
            investigation=self.investigation,
            achievement_manager=self.achievement_manager,
            location_manager=self.location_manager,
        )

    def load_game(self, slot_name: str = "slot_1") -> bool:
        """Load a previously saved session from a named slot.

        Restores the player, the case (including its saved
        solved/failed/in-progress status), evidence/clue discovery
        flags, suspect interrogation state, and `GameState`'s own
        tracked fields (score, accuracy, rank, discovered ids,
        interrogation history, hints used, etc.).

        If the case was still in progress when saved, an active
        `Investigation` is rebuilt so play can continue seamlessly
        (`explore_location`, `discover_evidence`, `examine_suspect`,
        and so on all work immediately). If the case had already been
        solved or failed, the investigation is not resumed (there is
        nothing left to investigate) -- only the final state is
        restored for review.

        Any in-progress `Interrogation` at the moment of saving is not
        replayed (asked-but-unanswered questions aren't persisted);
        `interrogation_history` (completed interrogation summaries)
        is restored, but `start_interrogation()` must be called again
        to interrogate further.

        Args:
            slot_name: Slot identifier to load from.

        Returns:
            True if a save was found and successfully restored, False
            otherwise (e.g. missing/corrupt save, or the case it
            refers to can no longer be loaded).
        """
        info = self.save_manager.get_save_info(slot_name)
        if info is None:
            return False

        case_id = info.get("case_id")
        if not case_id:
            return False

        if self.case is None or self.case.case_id != case_id:
            try:
                self.load_case(case_id)
            except KeyError:
                return False

        loaded_state = self.save_manager.load_game(
            slot_name,
            case_manager=self.case_manager,
            evidence_manager=self.evidence_manager,
            clue_manager=self.clue_manager,
            suspect_manager=self.suspect_manager,
            location_manager=self.location_manager,
        )
        if loaded_state is None:
            return False

        # Keep a single Case object as the source of truth: reuse the
        # one already registered with case_manager/evidence/clue data
        # (self.case), just overlay its saved status onto it, rather
        # than swapping in the standalone Case that SaveManager
        # reconstructed from case_data.
        if loaded_state.case is not None and self.case is not None:
            self.case.status = loaded_state.case.status
        loaded_state.case = self.case

        self.player = loaded_state.player if loaded_state.player is not None else self.player
        self.game_state = loaded_state
        self.game_state.player = self.player

        achievement_data = self.save_manager.load_achievement_state(slot_name)
        self.achievement_manager = AchievementManager.from_dict(achievement_data)

        self._hints_used = self.game_state.hints_used
        self._unnecessary_actions = self.game_state.unnecessary_actions
        self._last_interrogation_outcome = (
            self.game_state.interrogation_history[-1]
            if self.game_state.interrogation_history
            else None
        )

        # Only rebuild a live Investigation if there's still an active
        # case to investigate -- a solved/failed case has nothing left
        # to discover, and Investigation.start_investigation() would
        # reject it anyway (Case.start() forbids restarting a
        # solved/failed case).
        self.interrogation = None
        self.game_state.interrogation = None
        if self.case is not None and self.case.status not in ("solved", "failed"):
            investigation = Investigation(
                case_manager=self.case_manager,
                evidence_manager=self.evidence_manager,
                clue_manager=self.clue_manager,
                suspect_manager=self.suspect_manager,
                investigator=self.player.name,
                location_manager=self.location_manager,
            )
            inv_state = self.save_manager.load_investigation_state(slot_name)
            if inv_state is not None:
                investigation.load_state(
                    self.case,
                    status=inv_state["status"],
                    visited_locations=inv_state["visited_locations"],
                    examined_suspects=inv_state["examined_suspects"],
                    history=inv_state["history"],
                    current_location_id=inv_state.get("current_location_id"),
                )
            else:
                investigation.load_state(self.case, status="active")

            self.investigation = investigation
            self.game_state.investigation = investigation
        else:
            self.investigation = None
            self.game_state.investigation = None

        return True

    def has_save(self, slot_name: str = "slot_1") -> bool:
        """Return True if a save exists for `slot_name`."""
        return self.save_manager.save_exists(slot_name)

    def list_saves(self) -> List[Dict[str, Any]]:
        """Return metadata summaries for every save slot on disk."""
        return self.save_manager.list_saves()

    def delete_save(self, slot_name: str = "slot_1") -> bool:
        """Delete the save in `slot_name`, if it exists."""
        return self.save_manager.delete_save(slot_name)

    # -- Achievements -----------------------------------------------------------

    def _build_achievement_stats(
        self,
        solved: Optional[bool] = None,
        action_count: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Build the flat statistics dictionary `AchievementManager` consumes.

        This is the single place that reads across `Player`,
        `GameState`, `Investigation`, and `ScoreManager` to assemble
        achievement-checkable statistics -- `AchievementManager`
        itself never touches those modules directly, so this method
        is intentionally the only bridge between them and it.

        Args:
            solved: Whether the just-concluded case was solved
                correctly. Only meaningful right after
                `conclude_case`; omitted (None) during mid-case
                discovery checks, where it simply isn't a relevant
                statistic yet.
            action_count: Total investigation action count for the
                just-concluded case, used for the "solved within the
                target time" statistic. Omitted (None) mid-case for
                the same reason as `solved`.

        Returns:
            A flat dict of statistic name -> value, safe to pass to
            `AchievementManager.check_achievements`.
        """
        stats: Dict[str, Any] = {
            "cases_solved": self.player.cases_solved,
            "hints_used": self.game_state.hints_used,
            "no_hints_used": self.game_state.hints_used == 0,
            "unnecessary_actions": self.game_state.unnecessary_actions,
            "score": self.score_manager.current_score,
            "accuracy": self.score_manager.current_accuracy,
            "rank": self.score_manager.get_rank(),
        }

        if self.investigation is not None:
            progress = self.investigation.get_progress()
            evidence_total = progress.get("evidence_total", 0)
            evidence_discovered = progress.get("evidence_discovered", 0)
            clues_total = progress.get("clues_total", 0)
            clues_discovered = progress.get("clues_discovered", 0)

            stats["evidence_total"] = evidence_total
            stats["evidence_discovered"] = evidence_discovered
            stats["clues_total"] = clues_total
            stats["clues_discovered"] = clues_discovered
            stats["all_evidence_discovered"] = (
                evidence_total > 0 and evidence_discovered >= evidence_total
            )
            stats["all_clues_discovered"] = (
                clues_total > 0 and clues_discovered >= clues_total
            )

        if solved is not None:
            stats["solved"] = solved

        if action_count is not None:
            target = self.score_manager.config.time_bonus_action_threshold
            stats["action_count"] = action_count
            stats["within_target_time"] = action_count <= target

        return stats

    def get_achievements(self) -> List[Achievement]:
        """Return every registered achievement (locked and unlocked)."""
        return self.achievement_manager.get_all_achievements()

    def get_unlocked_achievements(self) -> List[Achievement]:
        """Return every currently unlocked achievement."""
        return self.achievement_manager.get_unlocked_achievements()

    def get_achievement_progress(self) -> Dict[str, Any]:
        """Return a summary snapshot of overall achievement progress."""
        return self.achievement_manager.get_progress()

    # -- Internal helpers ------------------------------------------------------

    def _require_case(self) -> Case:
        if self.case is None:
            raise RuntimeError("No case loaded; call load_case() first")
        return self.case

    def _require_investigation(self) -> Investigation:
        if self.investigation is None:
            raise RuntimeError(
                "No active investigation; call start_investigation() first"
            )
        return self.investigation

    def _require_interrogation(self) -> Interrogation:
        if self.interrogation is None:
            raise RuntimeError(
                "No active interrogation; call start_interrogation() first"
            )
        return self.interrogation

    def __repr__(self) -> str:
        case_id = self.case.case_id if self.case is not None else None
        return f"GameController(case_id={case_id!r}, player={self.player.name!r})"
