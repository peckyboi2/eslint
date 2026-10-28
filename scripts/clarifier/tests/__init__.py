"""Deterministic clarifier test package. Serves tasks 08–15, R1 and R2."""
import sys
from pathlib import Path

_PACKAGE_PARENT = str(Path(__file__).resolve().parents[2])
if _PACKAGE_PARENT not in sys.path:
    sys.path.insert(0, _PACKAGE_PARENT)
