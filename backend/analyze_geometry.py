"""Thin wrapper so `python analyze_geometry.py <file.step>` works as written in the PRD."""

import sys

from geometry.cli import main

if __name__ == "__main__":
    sys.exit(main())
