"""IoT Device Manager - Main entry point.

Run this file to start the app:
    python main.py

Or run as module:
    python -m src.iot_manager
"""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from iot_manager.app import main

if __name__ == "__main__":
    main()
