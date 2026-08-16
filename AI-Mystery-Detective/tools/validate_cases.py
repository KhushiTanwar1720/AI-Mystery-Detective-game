"""
Validates every case in cases/ end-to-end against the real backend:

- Loads it via GameController (case + suspects + evidence + clues + locations)
- Confirms correct_suspect is one of the case's registered suspects
- Confirms every evidence/clue related_suspects entry refers to a real suspect name
- Confirms every location's available_evidence/available_clues ids exist
- Confirms the location graph is connected (every location reachable from the first)
- Confirms suspect names in case.suspects all resolve to real Suspect objects
- Actually plays the case end-to-end: visits every location, discovers all
  evidence/clues, interrogates every suspect, runs AI analysis, and submits
  the correct accusation to confirm the case can be solved and completed.

Run with:
    python tools/validate_cases.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from game.game_controller import GameController  # noqa: E402

CASES_DIR = Path(__file__).resolve().parent.parent / "cases"


def validate_case(case_id: str) -> list[str]:
    errors: list[str] = []
    gc = GameController(player_id="validator", player_name="Validator", cases_dir=str(CASES_DIR))
    try:
        case = gc.load_case(case_id)
    except Exception as exc:  # noqa: BLE001
        return [f"{case_id}: failed to load: {exc}"]

    # Suspects referenced by the case must resolve to real Suspect objects.
    suspects = gc.get_case_suspects()
    suspect_names = {s.name for s in suspects}
    for name in case.suspects:
        if name not in suspect_names:
            errors.append(f"{case_id}: suspect '{name}' listed on case but not found in suspects file")

    if case.correct_suspect not in suspect_names:
        errors.append(f"{case_id}: correct_suspect '{case.correct_suspect}' not among loaded suspects {sorted(suspect_names)}")

    # Evidence/clue related_suspects must point to real suspect names.
    for ev in gc.evidence_manager.get_all_evidence():
        if ev.evidence_id not in case.evidence:
            continue
        for rs in ev.related_suspects:
            if rs not in suspect_names:
                errors.append(f"{case_id}: evidence '{ev.evidence_id}' references unknown suspect '{rs}'")

    for cl in gc.clue_manager.get_all_clues():
        if cl.clue_id not in case.clues:
            continue
        for rs in cl.related_suspects:
            if rs not in suspect_names:
                errors.append(f"{case_id}: clue '{cl.clue_id}' references unknown suspect '{rs}'")

    # Location graph checks.
    locations = gc.location_manager.get_all_locations()
    loc_ids = {loc.location_id for loc in locations}
    ev_ids = {ev.evidence_id for ev in gc.evidence_manager.get_all_evidence()}
    cl_ids = {cl.clue_id for cl in gc.clue_manager.get_all_clues()}

    for loc in locations:
        for conn in loc.connected_locations:
            if conn not in loc_ids:
                errors.append(f"{case_id}: location '{loc.location_id}' connects to unknown location '{conn}'")
        for eid in loc.available_evidence:
            if eid not in ev_ids:
                errors.append(f"{case_id}: location '{loc.location_id}' references unknown evidence '{eid}'")
        for cid in loc.available_clues:
            if cid not in cl_ids:
                errors.append(f"{case_id}: location '{loc.location_id}' references unknown clue '{cid}'")

    if locations:
        # Connectivity (undirected reachability) from the first location.
        adj: dict[str, set[str]] = {loc.location_id: set(loc.connected_locations) for loc in locations}
        for loc in locations:
            for conn in loc.connected_locations:
                adj.setdefault(conn, set()).add(loc.location_id)
        seen = {locations[0].location_id}
        stack = [locations[0].location_id]
        while stack:
            cur = stack.pop()
            for nxt in adj.get(cur, ()):  # noqa: E501
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        unreachable = loc_ids - seen
        if unreachable:
            errors.append(f"{case_id}: unreachable locations {sorted(unreachable)}")

        # Every evidence/clue id on the case must be placed in at least one location.
        placed_ev = {eid for loc in locations for eid in loc.available_evidence}
        placed_cl = {cid for loc in locations for cid in loc.available_clues}
        for eid in case.evidence:
            if eid not in placed_ev:
                errors.append(f"{case_id}: evidence '{eid}' is not placed at any location")
        for cid in case.clues:
            if cid not in placed_cl:
                errors.append(f"{case_id}: clue '{cid}' is not placed at any location")

    # -- Full end-to-end playthrough -----------------------------------
    try:
        gc.start_investigation()
        for loc in gc.get_available_locations():
            gc.explore_location_by_id(loc.location_id)
        for eid in list(case.evidence):
            try:
                gc.discover_evidence(eid)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{case_id}: could not discover evidence '{eid}': {exc}")
        for cid in list(case.clues):
            try:
                gc.discover_clue(cid)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{case_id}: could not discover clue '{cid}': {exc}")
        for suspect in suspects:
            gc.start_interrogation(suspect.suspect_id)
            q = gc.ask_question("Where were you at the time of the incident?", category="alibi")
            gc.record_answer(q.question_id, suspect.alibi)
            gc.end_interrogation()
        gc.run_ai_analysis()
        result = gc.conclude_case(case.correct_suspect)
        if not result.get("solved"):
            errors.append(f"{case_id}: submitting correct_suspect did not resolve as correct: {result}")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"{case_id}: end-to-end playthrough failed: {exc}")

    return errors


def main() -> int:
    case_ids = sorted(p.stem for p in CASES_DIR.glob("case_*.json"))
    all_errors: list[str] = []
    for cid in case_ids:
        errs = validate_case(cid)
        status = "OK" if not errs else f"{len(errs)} ISSUE(S)"
        print(f"{cid}: {status}")
        all_errors.extend(errs)

    if all_errors:
        print("\n--- ISSUES ---")
        for e in all_errors:
            print(" -", e)
        return 1

    print(f"\nAll {len(case_ids)} cases validated successfully (full end-to-end playthrough).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
