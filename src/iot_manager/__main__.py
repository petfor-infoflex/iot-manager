"""Entry point for running as a module: python -m iot_manager"""

import sys
from pathlib import Path

# Ensure the package can be imported when running as frozen exe
if getattr(sys, 'frozen', False):
    # Running as compiled
    app_path = Path(sys.executable).parent
    if str(app_path) not in sys.path:
        sys.path.insert(0, str(app_path))
    from iot_manager.app import main
else:
    # Running as script
    from .app import main

if __name__ == "__main__":
    main()
