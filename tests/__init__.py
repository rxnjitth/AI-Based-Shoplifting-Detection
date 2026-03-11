"""Tests package initialization."""

import sys
from pathlib import Path

# Ensure imports like `from app...` resolve to backend/app during tests and editor analysis.
BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
if str(BACKEND_DIR) not in sys.path:
	sys.path.insert(0, str(BACKEND_DIR))
