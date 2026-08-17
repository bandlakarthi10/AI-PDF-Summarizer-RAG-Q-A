"""pytest configuration: adds backend/ to sys.path and declares asyncio mode."""
import sys
from pathlib import Path

# Ensure `app` package is importable from the backend directory
BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))
