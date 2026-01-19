"""IoT Device Manager - Huvudingång.

Kör denna fil för att starta appen:
    python main.py

Eller kör som modul:
    python -m src.iot_manager
"""

import sys
from pathlib import Path

# Lägg till src i sökvägen
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from iot_manager.app import main

if __name__ == "__main__":
    main()
