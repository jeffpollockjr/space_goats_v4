#!/usr/bin/env python3
"""Run from VS Code's terminal: python run_simulations.py --players 4."""

import sys

if sys.version_info < (3, 10):
    raise SystemExit("Space Goats requires Python 3.10 or newer.")

from space_goats.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
