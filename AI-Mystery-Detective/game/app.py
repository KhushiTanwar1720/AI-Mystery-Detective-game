"""
Application controller for AI Mystery Detective.

This module defines the `App` class, the single entry point into the
game's runtime. `App` does not implement any gameplay rules itself --
it delegates everything to `GameController` (see `game.game_controller`),
which wires together the existing `Case`, `Player`, `Investigation`,
`Interrogation`, and `AIAnalyzer` modules.

`App` currently drives a scripted, fully-automated playthrough of a
case (visiting every location, discovering all evidence/clues,
examining every suspect, interrogating one, running the AI analyzer,
and concluding the case) and prints a narration of each stage to the
console. This is intentionally *not* a full UI: there's no menu, no
player input, no rendering layer. It exists so that `python main.py`
demonstrably exercises the real backend game flow end-to-end instead
of only printing a startup banner. A future `ui` module can replace
`_run_scripted_playthrough` with real player interaction while
reusing the exact same `GameController` API.
"""

from __future__ import annotations

from typing import Optional

from game.game_controller import GameController


class App:
    """Top-level application controller.

    Bootstraps a `GameController` game session and drives it through
    a complete case from start to conclusion, printing progress along
    the way. Future versions may hand off to a `MainMenu`
    (`game/menu.py`, not yet created) that drives Start/Continue/
    Settings/Exit flows and real player interaction; that layer would
    sit on top of `GameController` the same way this scripted
    playthrough does.
    """

    def __init__(
        self,
        name: str = "AI Mystery Detective",
        player_id: str = "player_1",
        player_name: str = "Detective",
    ) -> None:
        self.name = name
        self.running = False
        self.player_id = player_id
        self.player_name = player_name
        self.controller: Optional[GameController] = None

    def start(self, case_id: str = "case_001") -> GameController:
        """Start the application and play through `case_id` end to end.

        Args:
            case_id: Id of the case to play. Defaults to "case_001",
                the sample case shipped with full suspect/evidence/clue
                data.

        Returns:
            The `GameController` used for the session, so callers
            (tests, a future UI layer) can inspect its final state.
        """
        self.running = True
        print(f"{self.name} - starting investigation system.")

        self.controller = GameController(
            player_id=self.player_id,
            player_name=self.player_name,
        )
        self._run_scripted_playthrough(self.controller, case_id)

        self.shutdown()
        return self.controller

    def shutdown(self) -> None:
        """Cleanly stop the application."""
        self.running = False

    # -- Scripted playthrough -----------------------------------------------

    @staticmethod
    def _run_scripted_playthrough(controller: GameController, case_id: str) -> None:
        """Drive `controller` through one full game flow, narrating it.

        Flow: load case -> start investigation -> explore every known
        location, discovering evidence/clues -> examine every suspect
        -> interrogate one suspect -> run the AI analyzer -> accuse
        the analyzer's top suspect and conclude the case.
        """
        case = controller.load_case(case_id)
        print(f"\nCase loaded: {case.title} ({case.case_id})")
        print(f"  {case.description}")

        controller.start_investigation()
        print(f"\nInvestigation started by {controller.player.name}.")

        locations = controller.get_case_locations()
        for location in locations:
            info = controller.explore_location(location)
            for evidence_info in info["evidence_here"]:
                if not evidence_info["discovered"]:
                    controller.discover_evidence(evidence_info["evidence_id"])
            for clue_info in info["clues_here"]:
                if not clue_info["discovered"]:
                    controller.discover_clue(clue_info["clue_id"])
        progress = controller.investigation.get_progress()
        print(
            f"\nExplored {len(locations)} location(s): "
            f"{progress['evidence_discovered']}/{progress['evidence_total']} evidence, "
            f"{progress['clues_discovered']}/{progress['clues_total']} clues discovered."
        )

        suspects = controller.get_case_suspects()
        for suspect in suspects:
            controller.examine_suspect(suspect.suspect_id)
        print(f"Examined {len(suspects)} suspect(s): " + ", ".join(s.name for s in suspects))

        if suspects:
            target = suspects[0]
            controller.start_interrogation(target.suspect_id)
            question = controller.ask_question(
                "Where were you when the incident occurred?", category="alibi"
            )
            controller.record_answer(question.question_id, target.alibi)
            interrogation_outcome = controller.end_interrogation()
            print(
                f"\nInterrogated {target.name}: "
                f"{interrogation_outcome['answers_recorded']} answer(s) recorded, "
                f"{len(interrogation_outcome['contradictions'])} contradiction(s) found."
            )

        analysis = controller.run_ai_analysis()
        print(f"\n{analysis.summary}")
        print(analysis.data.get("narrative", ""))

        scores = analysis.data.get("suspicion_scores", {}).get("data", {}).get("scores", [])
        if scores:
            accused = scores[0]["name"]
            outcome = controller.conclude_case(accused)
            result = "correctly" if outcome["solved"] else "incorrectly"
            print(
                f"\nFinal accusation: {accused} -- {result} accused. "
                f"Case status: {outcome['case_status']}."
            )
            score_info = outcome.get("score_info", {})
            rank = score_info.get("rank", "Unknown")
            accuracy = score_info.get("accuracy", 0.0)
            print(
                f"\nPlayer score: {controller.player.investigation_score} "
                f"| Accuracy: {accuracy}% | Rank: {rank}"
            )
        else:
            print("\nNot enough data to make an accusation.")

