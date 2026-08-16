"""
AI Mystery Detective - application entry point.

Run this file to launch the project. All actual logic lives in the
`game`, `ai`, and `database` packages -- this file only wires the
entry point together and hands off control to the App controller.
"""

from game.app import App


def main() -> None:
    app = App()
    app.start()


if __name__ == "__main__":
    main()
