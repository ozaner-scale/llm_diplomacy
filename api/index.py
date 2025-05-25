"""Vercel API handler for the Diplomacy web application."""

import sys
from pathlib import Path

# Add parent directory to path so we can import from the root
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import app

# Vercel expects a handler named 'app'
# Our FastAPI app is already named 'app', so we can use it directly
