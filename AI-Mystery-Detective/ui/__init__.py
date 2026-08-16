"""
ui package
==========
Graphical (Pygame) presentation layer for AI Mystery Detective.

This package is kept strictly separate from game logic: every screen
and component here calls into `game.game_controller.GameController`
(and the objects it returns) for anything resembling gameplay state
or rules. Nothing in `ui/` re-implements investigation, evidence,
clue, suspect, interrogation, AI-analysis, scoring, achievement, or
save/load logic.

`ui/campaign.py` is intentionally free of any `import pygame` so it
(and the tests that exercise it) work in environments without pygame
installed. Everything else here (`ui/theme.py`, `ui/app.py`,
`ui/state_manager.py`, `ui/components/`, `ui/screens/`) does depend
on pygame and is therefore not imported by this `__init__.py` --
importing `ui` itself must never require pygame to be installed.
"""
