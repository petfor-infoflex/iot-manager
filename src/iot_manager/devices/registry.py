"""Device registry for managing all connected devices."""

from typing import Optional, Callable
from .base import BaseDevice, DeviceType
import logging

logger = logging.getLogger(__name__)


class DeviceRegistry:
    """Registry for managing IoT devices.

    Provides a central place to store, retrieve, and manage devices.
    """

    def __init__(self):
        self._devices: dict[str, BaseDevice] = {}
        self._on_device_added: list[Callable[[BaseDevice], None]] = []
        self._on_device_removed: list[Callable[[str], None]] = []
        self._on_device_updated: list[Callable[[BaseDevice], None]] = []

    @property
    def devices(self) -> list[BaseDevice]:
        """Get all registered devices."""
        return list(self._devices.values())

    @property
    def device_count(self) -> int:
        """Get the number of registered devices."""
        return len(self._devices)

    def add_device(self, device: BaseDevice) -> bool:
        """Add a device to the registry.

        Args:
            device: The device to add

        Returns:
            True if device was added, False if it already exists
        """
        if device.device_id in self._devices:
            logger.debug(f"Device {device.device_id} already in registry")
            return False

        self._devices[device.device_id] = device
        logger.info(f"Added device: {device.name} ({device.device_id})")

        for callback in self._on_device_added:
            try:
                callback(device)
            except Exception as e:
                logger.error(f"Error in device added callback: {e}")

        return True

    def remove_device(self, device_id: str) -> Optional[BaseDevice]:
        """Remove a device from the registry.

        Args:
            device_id: ID of the device to remove

        Returns:
            The removed device, or None if not found
        """
        device = self._devices.pop(device_id, None)

        if device:
            logger.info(f"Removed device: {device.name} ({device_id})")

            for callback in self._on_device_removed:
                try:
                    callback(device_id)
                except Exception as e:
                    logger.error(f"Error in device removed callback: {e}")

        return device

    def get_device(self, device_id: str) -> Optional[BaseDevice]:
        """Get a device by its ID.

        Args:
            device_id: ID of the device to get

        Returns:
            The device, or None if not found
        """
        return self._devices.get(device_id)

    def get_devices_by_type(self, device_type: DeviceType) -> list[BaseDevice]:
        """Get all devices of a specific type.

        Args:
            device_type: The type of devices to get

        Returns:
            List of devices of the specified type
        """
        return [d for d in self._devices.values() if d.device_type == device_type]

    def get_online_devices(self) -> list[BaseDevice]:
        """Get all online devices.

        Returns:
            List of devices that are currently online
        """
        return [d for d in self._devices.values() if d.is_online]

    def update_device(self, device: BaseDevice) -> None:
        """Notify that a device has been updated.

        Args:
            device: The updated device
        """
        if device.device_id not in self._devices:
            return

        for callback in self._on_device_updated:
            try:
                callback(device)
            except Exception as e:
                logger.error(f"Error in device updated callback: {e}")

    def on_device_added(self, callback: Callable[[BaseDevice], None]) -> None:
        """Register a callback for when devices are added.

        Args:
            callback: Function to call with the new device
        """
        self._on_device_added.append(callback)

    def on_device_removed(self, callback: Callable[[str], None]) -> None:
        """Register a callback for when devices are removed.

        Args:
            callback: Function to call with the removed device ID
        """
        self._on_device_removed.append(callback)

    def on_device_updated(self, callback: Callable[[BaseDevice], None]) -> None:
        """Register a callback for when devices are updated.

        Args:
            callback: Function to call with the updated device
        """
        self._on_device_updated.append(callback)

    def clear(self) -> None:
        """Remove all devices from the registry."""
        device_ids = list(self._devices.keys())
        for device_id in device_ids:
            self.remove_device(device_id)

    def __contains__(self, device_id: str) -> bool:
        """Check if a device is in the registry."""
        return device_id in self._devices

    def __len__(self) -> int:
        """Get the number of devices."""
        return len(self._devices)

    def __iter__(self):
        """Iterate over devices."""
        return iter(self._devices.values())
