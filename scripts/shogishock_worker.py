#!/usr/bin/env python3
"""Repository-local entry point; no engine work at import time."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from surprise.research_worker import main

if __name__ == '__main__':
    raise SystemExit(main())
