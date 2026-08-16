"""
Campaign manifest for the AI Mystery Detective UI.

This module is intentionally free of any UI-framework (pygame)
import so it can be loaded and unit-tested in any environment,
including one where pygame isn't installed.

It has two responsibilities, and does not duplicate backend logic
for either:

1. Load the *design-target* level list (title, subtitle, difficulty
   stars, horror rating, flavor location names) from
   `data/campaign.json`. This is presentation metadata only -- it
   never invents gameplay data (evidence, clues, suspects) that the
   backend doesn't actually have.

2. Resolve, for each level, whether it is *actually playable* right
   now, by checking whether the backend has real case/evidence/clue/
   suspect data on disk for it (via `game.case.CaseManager` and the
   same `cases/<subfolder>/<case_id>_*.json` convention
   `GameController._load_case_data` already uses) -- and resolve its
   completion/lock status from the existing `Player`/`GameState`/
   `Case` objects a live `GameController` already owns. No second
   progression system is created: "completed" comes from
   `Case.status`, "unlocked" comes from `Player.cases_solved`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_CAMPAIGN_PATH = Path(__file__).resolve().parent.parent / "data" / "campaign.json"

# Statuses a level can show on the case-selection screen. These are
# UI-facing labels only -- the underlying truth is always read from
# `Case.status` / `Player.cases_solved`, never stored here.
LEVEL_STATUS_LOCKED = "locked"
LEVEL_STATUS_AVAILABLE = "available"
LEVEL_STATUS_IN_PROGRESS = "in_progress"
LEVEL_STATUS_COMPLETED = "completed"
LEVEL_STATUS_NOT_YET_BUILT = "not_yet_built"


@dataclass
class LevelInfo:
    """One entry in the campaign manifest, plus resolved runtime status.

    Attributes:
        level_number: 1-based position in the campaign.
        case_id: Id of the backend `Case` this level maps to, or None
            if this level is a design target with no backend data yet.
        title: Display title.
        subtitle: Secondary display line (e.g. the setting).
        difficulty_stars: 1-5 star difficulty rating for display.
        horror_rating: 1-10 horror intensity rating for display.
        locations: Flavor location names for the case-selection card
            (display only -- the real explorable locations come from
            `LocationManager`/`Case.locations` once a case is loaded).
        has_backend_data: True if real case/evidence/clue/location/
            suspect files exist on disk for `case_id`. False for
            every level whose `case_id` is None, and also False for a
            `case_id` that exists only as a bare case JSON with no
            supporting evidence/clue/location/suspect files (i.e.
            not actually playable end-to-end).
        status: One of the `LEVEL_STATUS_*` constants, resolved by
            `resolve_status()`.
    """

    level_number: int
    case_id: Optional[str]
    title: str
    subtitle: str
    difficulty_stars: int
    horror_rating: int
    locations: List[str] = field(default_factory=list)
    has_backend_data: bool = False
    status: str = LEVEL_STATUS_NOT_YET_BUILT

    def difficulty_display(self) -> str:
        """Return a star-rating string, e.g. '\u2605\u2605\u2606\u2606\u2606'."""
        filled = max(0, min(5, self.difficulty_stars))
        return ("\u2605" * filled) + ("\u2606" * (5 - filled))

    def horror_display(self) -> str:
        """Return a bar-rating string for the horror intensity out of 10."""
        filled = max(0, min(10, self.horror_rating))
        return ("\U0001F52E" * 0) + ("\u25A0" * filled) + ("\u25A1" * (10 - filled))

    def is_playable(self) -> bool:
        """Return True if this level can actually be started right now."""
        return self.has_backend_data and self.status not in (
            LEVEL_STATUS_LOCKED,
            LEVEL_STATUS_NOT_YET_BUILT,
        )


def load_campaign_manifest(path: Optional[Path] = None) -> List[LevelInfo]:
    """Load the raw campaign design-target list from `data/campaign.json`.

    This does not check backend availability or resolve status --
    see `resolve_availability` / `resolve_status` for that. Callers
    almost always want `load_campaign` instead, which does both in
    one call.

    Args:
        path: Optional override path to the manifest JSON. Defaults
            to `data/campaign.json` at the project root.

    Returns:
        A list of `LevelInfo`, in `level_number` order, with
        `has_backend_data=False` and `status=LEVEL_STATUS_NOT_YET_BUILT`
        for every entry (unresolved).

    Raises:
        FileNotFoundError: If the manifest file doesn't exist.
        ValueError: If the manifest JSON is malformed.
    """
    manifest_path = Path(path) if path is not None else DEFAULT_CAMPAIGN_PATH
    if not manifest_path.exists():
        raise FileNotFoundError(f"Campaign manifest not found: {manifest_path}")

    try:
        with open(manifest_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Campaign manifest is not valid JSON: {exc}") from exc

    levels_raw = data.get("levels", []) if isinstance(data, dict) else []

    levels: List[LevelInfo] = []
    for entry in levels_raw:
        if not isinstance(entry, dict):
            continue
        try:
            levels.append(
                LevelInfo(
                    level_number=int(entry["level_number"]),
                    case_id=entry.get("case_id"),
                    title=str(entry["title"]),
                    subtitle=str(entry.get("subtitle", "")),
                    difficulty_stars=int(entry.get("difficulty_stars", 1)),
                    horror_rating=int(entry.get("horror_rating", 1)),
                    locations=[str(loc) for loc in entry.get("locations", [])],
                )
            )
        except (KeyError, TypeError, ValueError):
            # Malformed entry -- skip rather than crash the UI over
            # one bad manifest row.
            continue

    levels.sort(key=lambda lvl: lvl.level_number)
    return levels


def _case_has_full_backend_data(case_id: str, cases_dir: Path) -> bool:
    """Check (on disk, without instantiating a GameController) whether
    `case_id` has a case file plus every supporting data file that
    `GameController._load_case_data` looks for.

    A level only counts as backend-playable if a player could
    actually load it, explore locations, and discover evidence/clues
    -- not merely if a bare case JSON with an empty suspects list
    exists (see `case_002` in this project: a real case file with no
    evidence/clue/location/suspect files behind it).
    """
    case_file = cases_dir / f"{case_id}.json"
    if not case_file.exists():
        return False

    required_subfiles = (
        cases_dir / "suspects" / f"{case_id}_suspects.json",
        cases_dir / "evidence" / f"{case_id}_evidence.json",
        cases_dir / "clues" / f"{case_id}_clues.json",
    )
    return all(f.exists() for f in required_subfiles)


def resolve_availability(levels: List[LevelInfo], cases_dir: Path) -> None:
    """Set `has_backend_data` on each `LevelInfo` in place.

    Args:
        levels: Levels to resolve (mutated in place).
        cases_dir: The backend's `cases/` directory (see
            `game.case.CaseManager`).
    """
    cases_dir = Path(cases_dir)
    for level in levels:
        level.has_backend_data = bool(
            level.case_id and _case_has_full_backend_data(level.case_id, cases_dir)
        )


def resolve_status(
    levels: List[LevelInfo],
    player: Optional[Any] = None,
    case_manager: Optional[Any] = None,
) -> None:
    """Set `status` on each `LevelInfo` in place.

    Status is derived entirely from existing backend objects -- no
    second progression store is created:

    - A level with no backend data is `LEVEL_STATUS_NOT_YET_BUILT`
      (a design target, not yet content).
    - The first backend-playable level is always at least
      `LEVEL_STATUS_AVAILABLE`.
    - A later backend-playable level is `LEVEL_STATUS_LOCKED` unless
      `player.cases_solved` is at least the count of backend-playable
      levels before it (i.e. the campaign unlocks sequentially as the
      player actually solves cases -- read from `Player`, not stored
      here).
    - If `case_manager` is given and has already loaded the level's
      `Case` (e.g. the player started it in a previous session),
      `Case.status` overrides the sequential guess with the real
      status: "solved" -> `LEVEL_STATUS_COMPLETED`, "in_progress" ->
      `LEVEL_STATUS_IN_PROGRESS`.

    Args:
        levels: Levels to resolve (mutated in place). Must already
            have `has_backend_data` set via `resolve_availability`.
        player: Optional `game.player.Player` instance, used for
            `cases_solved`-based sequential unlocking. If None, every
            backend-playable level is treated as available (nothing
            gated) -- suitable for a fresh, no-player-yet preview.
        case_manager: Optional `game.case.CaseManager` instance, used
            to read the real status of any already-loaded `Case`.
    """
    cases_solved = int(getattr(player, "cases_solved", 0) or 0) if player is not None else None

    playable_seen = 0
    for level in levels:
        if not level.has_backend_data:
            level.status = LEVEL_STATUS_NOT_YET_BUILT
            continue

        if cases_solved is None:
            level.status = LEVEL_STATUS_AVAILABLE
        elif playable_seen <= cases_solved:
            level.status = LEVEL_STATUS_AVAILABLE
        else:
            level.status = LEVEL_STATUS_LOCKED

        if case_manager is not None and level.case_id:
            case = case_manager.get_case(level.case_id)
            if case is not None:
                if case.get_status() == "solved":
                    level.status = LEVEL_STATUS_COMPLETED
                elif case.get_status() == "in_progress":
                    level.status = LEVEL_STATUS_IN_PROGRESS

        playable_seen += 1


def load_campaign(
    cases_dir: Path,
    player: Optional[Any] = None,
    case_manager: Optional[Any] = None,
    manifest_path: Optional[Path] = None,
) -> List[LevelInfo]:
    """Load the campaign manifest and fully resolve every level's status.

    Convenience wrapper combining `load_campaign_manifest`,
    `resolve_availability`, and `resolve_status`.

    Args:
        cases_dir: The backend's `cases/` directory.
        player: Optional `Player` for sequential-unlock resolution.
        case_manager: Optional `CaseManager` for real per-case status.
        manifest_path: Optional override for the manifest JSON path.

    Returns:
        Fully resolved list of `LevelInfo`, in level order.
    """
    levels = load_campaign_manifest(manifest_path)
    resolve_availability(levels, Path(cases_dir))
    resolve_status(levels, player=player, case_manager=case_manager)
    return levels


def count_playable_levels(levels: List[LevelInfo]) -> int:
    """Return how many levels currently have real, playable backend data."""
    return sum(1 for level in levels if level.has_backend_data)
