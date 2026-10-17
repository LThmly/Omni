#!/usr/bin/env python3
"""Run the actual Pi UI upright, with a separate simulator data profile."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'firmware'))
from phone import main

if __name__ == '__main__':
    if '--sim' not in sys.argv:
        sys.argv.append('--sim')
    main()
