"""
game package
============
Core game logic lives here.

Foundation modules: `Player` (player.py), `Case`/`CaseManager`
(case.py), `Suspect`/`SuspectManager` (suspect.py),
`Evidence`/`EvidenceManager` (evidence.py), and `Clue`/`ClueManager`
(clue.py).

Higher-level modules: `Investigation` (investigation.py),
`Interrogation`/`Question`/`Statement` (interrogation.py), and
`AIAnalyzer`/`AnalysisResult`/`AIProvider`/`RuleBasedAIProvider`
(ai_analyzer.py).

Orchestration: `GameController` (game_controller.py) wires all of the
above into one playable backend flow (Case -> Player -> Investigation
-> Evidence/Clues -> Suspects -> Interrogation -> AI Analyzer ->
Investigation Result), and `App` (app.py) is the application entry
point that drives a `GameController` session.

Menu/state management, scoring, save/load, and UI rendering are not
implemented yet.
"""

from game.player import Player
from game.case import Case, CaseManager
from game.suspect import Suspect, SuspectManager
from game.evidence import Evidence, EvidenceManager
from game.clue import Clue, ClueManager
from game.location import Location, LocationManager
from game.investigation import Investigation
from game.interrogation import Interrogation, Question, Statement
from game.ai_analyzer import AIAnalyzer, AnalysisResult, AIProvider, RuleBasedAIProvider
from game.scoring import ScoreManager, ScoringConfig
from game.game_state import GameState
from game.save_manager import SaveManager
from game.achievement import Achievement, AchievementManager
from game.game_controller import GameController
from game.app import App

__all__ = [
    "Player",
    "Case",
    "CaseManager",
    "Suspect",
    "SuspectManager",
    "Evidence",
    "EvidenceManager",
    "Clue",
    "ClueManager",
    "Location",
    "LocationManager",
    "Investigation",
    "Interrogation",
    "Question",
    "Statement",
    "AIAnalyzer",
    "AnalysisResult",
    "AIProvider",
    "RuleBasedAIProvider",
    "ScoreManager",
    "ScoringConfig",
    "GameState",
    "SaveManager",
    "Achievement",
    "AchievementManager",
    "GameController",
    "App",
]



