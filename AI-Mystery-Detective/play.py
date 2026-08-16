"""
AI Mystery Detective -- graphical (Pygame) entry point.

`main.py` remains the CLI entry point (`game.app.App`), unchanged.
This script launches the graphical UI instead:

    python play.py

Requires pygame to be installed (`pip install pygame`).
"""

from ui.app import main

if __name__ == "__main__":
    main()
