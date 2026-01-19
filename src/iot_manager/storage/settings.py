"""Application settings management."""

import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class AppSettings:
    """Application settings with defaults."""

    # Appearance
    theme: str = "dark"  # "dark", "light", or "system"

    # Window
    window_width: int = 900
    window_height: int = 600
    start_minimized: bool = False

    # Discovery
    auto_discover: bool = True
    discovery_interval: int = 60  # seconds

    # Device polling
    polling_interval: int = 5  # seconds
    polling_enabled: bool = True

    # Stored devices (device configs that persist)
    saved_devices: list = field(default_factory=list)

    # TP-Link Tapo credentials (for Tapo lights)
    tapo_username: str = ""
    tapo_password: str = ""
    tapo_device_ips: list = field(default_factory=list)  # List of known Tapo device IPs

    # Tuya/Deltaco device configs (for Tuya-based lights)
    # Each item should have: name, ip, id, key, version (optional, default 3.3)
    tuya_devices: list = field(default_factory=list)


class SettingsManager:
    """Manages application settings persistence."""

    def __init__(self, app_name: str = "IoTDeviceManager"):
        """Initialize the settings manager.

        Args:
            app_name: Name of the application (used for config directory)
        """
        self._app_name = app_name
        self._settings_dir = self._get_settings_dir()
        self._settings_file = self._settings_dir / "settings.json"
        self._devices_file = self._settings_dir / "devices.json"
        self._settings: Optional[AppSettings] = None

    def _get_settings_dir(self) -> Path:
        """Get the appropriate settings directory for the platform."""
        if os.name == "nt":  # Windows
            base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        else:  # Linux/Mac
            base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))

        return base / self._app_name

    def load(self) -> AppSettings:
        """Load settings from disk or return defaults.

        Returns:
            The loaded or default settings
        """
        if self._settings is not None:
            return self._settings

        if self._settings_file.exists():
            try:
                with open(self._settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._settings = AppSettings(**data)
                    logger.info(f"Settings loaded from {self._settings_file}")
            except (json.JSONDecodeError, TypeError) as e:
                logger.warning(f"Failed to load settings, using defaults: {e}")
                self._settings = AppSettings()
        else:
            self._settings = AppSettings()
            logger.info("No settings file found, using defaults")

        return self._settings

    def save(self, settings: Optional[AppSettings] = None) -> None:
        """Save settings to disk.

        Args:
            settings: Settings to save (uses current if None)
        """
        if settings is not None:
            self._settings = settings

        if self._settings is None:
            return

        self._settings_dir.mkdir(parents=True, exist_ok=True)

        try:
            with open(self._settings_file, "w", encoding="utf-8") as f:
                json.dump(asdict(self._settings), f, indent=2)
            logger.info(f"Settings saved to {self._settings_file}")
        except IOError as e:
            logger.error(f"Failed to save settings: {e}")

    def update(self, **kwargs) -> AppSettings:
        """Update specific settings and save.

        Args:
            **kwargs: Setting names and values to update

        Returns:
            The updated settings
        """
        settings = self.load()

        for key, value in kwargs.items():
            if hasattr(settings, key):
                setattr(settings, key, value)
            else:
                logger.warning(f"Unknown setting: {key}")

        self.save(settings)
        return settings

    def load_devices(self) -> list[dict]:
        """Load saved device configurations.

        Returns:
            List of device configuration dicts
        """
        if self._devices_file.exists():
            try:
                with open(self._devices_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Failed to load devices: {e}")

        return []

    def save_devices(self, devices: list[dict]) -> None:
        """Save device configurations.

        Args:
            devices: List of device configuration dicts
        """
        self._settings_dir.mkdir(parents=True, exist_ok=True)

        try:
            with open(self._devices_file, "w", encoding="utf-8") as f:
                json.dump(devices, f, indent=2)
            logger.info(f"Devices saved to {self._devices_file}")
        except IOError as e:
            logger.error(f"Failed to save devices: {e}")

    def add_device(self, device_config: dict) -> None:
        """Add a device configuration.

        Args:
            device_config: Device configuration dict with at least 'id' key
        """
        devices = self.load_devices()

        # Update if exists, otherwise append
        device_id = device_config.get("id")
        for i, d in enumerate(devices):
            if d.get("id") == device_id:
                devices[i] = device_config
                break
        else:
            devices.append(device_config)

        self.save_devices(devices)

    def remove_device(self, device_id: str) -> None:
        """Remove a device configuration.

        Args:
            device_id: ID of the device to remove
        """
        devices = self.load_devices()
        devices = [d for d in devices if d.get("id") != device_id]
        self.save_devices(devices)

    @property
    def settings_dir(self) -> Path:
        """Get the settings directory path."""
        return self._settings_dir
