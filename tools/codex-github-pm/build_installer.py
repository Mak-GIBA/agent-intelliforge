#!/usr/bin/env python3
"""Regenerate the existing standalone format from readable canonical sources."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'intelliforge'))
from legacy_archive import main
if __name__ == '__main__': main(Path(__file__).resolve().parent)
