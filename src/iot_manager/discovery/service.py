"""Unified discovery service for IoT devices."""

from typing import Callable, Optional
from dataclasses import dataclass, field
import logging

from .mdns import MDNSDiscovery, DiscoveredDevice, ZEROCONF_AVAILABLE
from ..core.events import EventBus, Event, EventType

logger = logging.getLogger(__name__)


@dataclass
class DiscoveryResult:
    """Result from device discovery."""

    device_id: str
    name: str
    ip_address: Optional[str]
    port: int
    device_type: str
    source: str  # "mdns", "ssdp", "manual"
    properties: dict = field(default_factory=dict)

    def __hash__(self):
        return hash(self.device_id)


class DiscoveryService:
    """Unified service for discovering IoT devices.

    Combines multiple discovery methods (mDNS, SSDP) into a single interface.
    """

    def __init__(self, event_bus: Optional[EventBus] = None):
        """Initialize the discovery service.

        Args:
            event_bus: Optional event bus for publishing discovery events
        """
        self._event_bus = event_bus
        self._mdns = MDNSDiscovery()
        self._discovered: dict[str, DiscoveryResult] = {}
        self._on_device_found: list[Callable[[DiscoveryResult], None]] = []
        self._on_device_lost: list[Callable[[str], None]] = []
        self._running = False

    @property
    def is_running(self) -> bool:
        """Check if discovery is running."""
        return self._running

    @property
    def discovered_devices(self) -> list[DiscoveryResult]:
        """Get list of all discovered devices."""
        return list(self._discovered.values())

    def on_device_found(self, callback: Callable[[DiscoveryResult], None]) -> None:
        """Register callback for when devices are found.

        Args:
            callback: Function to call with discovery result
        """
        self._on_device_found.append(callback)

    def on_device_lost(self, callback: Callable[[str], None]) -> None:
        """Register callback for when devices are lost.

        Args:
            callback: Function to call with device ID
        """
        self._on_device_lost.append(callback)

    async def start(self) -> bool:
        """Start device discovery.

        Returns:
            True if at least one discovery method started successfully
        """
        if self._running:
            logger.warning("Discovery service already running")
            return True

        success = False

        # Start mDNS discovery
        if ZEROCONF_AVAILABLE:
            mdns_started = self._mdns.start(
                on_discovered=self._handle_mdns_discovered,
                on_removed=self._handle_device_removed,
            )
            if mdns_started:
                success = True
                logger.info("mDNS discovery started")
        else:
            logger.warning("mDNS discovery not available (zeroconf not installed)")

        if success:
            self._running = True

            if self._event_bus:
                self._event_bus.publish(Event(EventType.DISCOVERY_STARTED))

        return success

    async def stop(self) -> None:
        """Stop device discovery."""
        if not self._running:
            return

        self._running = False
        self._mdns.stop()

        if self._event_bus:
            self._event_bus.publish(Event(EventType.DISCOVERY_STOPPED))

        logger.info("Discovery service stopped")

    def _handle_mdns_discovered(self, device: DiscoveredDevice) -> None:
        """Handle device discovered via mDNS.

        Args:
            device: The discovered device info
        """
        # Create a unique ID from the service name
        device_id = f"mdns:{device.name}"

        result = DiscoveryResult(
            device_id=device_id,
            name=self._clean_name(device.name),
            ip_address=device.ip_address,
            port=device.port,
            device_type=device.device_type_hint,
            source="mdns",
            properties=device.properties,
        )

        # Check if this is a new device or update
        is_new = device_id not in self._discovered
        self._discovered[device_id] = result

        if is_new:
            logger.info(
                f"Discovered device: {result.name} ({result.device_type}) at {result.ip_address}"
            )

            # Notify callbacks
            for callback in self._on_device_found:
                try:
                    callback(result)
                except Exception as e:
                    logger.error(f"Error in device found callback: {e}")

            # Publish event
            if self._event_bus:
                self._event_bus.publish(
                    Event(EventType.DEVICE_DISCOVERED, data=result)
                )

    def _handle_device_removed(self, name: str) -> None:
        """Handle device removed.

        Args:
            name: The service name of the removed device
        """
        device_id = f"mdns:{name}"

        if device_id in self._discovered:
            del self._discovered[device_id]
            logger.info(f"Device removed: {name}")

            # Notify callbacks
            for callback in self._on_device_lost:
                try:
                    callback(device_id)
                except Exception as e:
                    logger.error(f"Error in device lost callback: {e}")

    def _clean_name(self, name: str) -> str:
        """Clean up a device name for display.

        Args:
            name: The raw service name

        Returns:
            A cleaner display name
        """
        # Remove common suffixes
        suffixes = [
            "._googlecast._tcp.local.",
            "._hue._tcp.local.",
            "._http._tcp.local.",
            "._airplay._tcp.local.",
            "._esphomelib._tcp.local.",
            "._homekit._tcp.local.",
        ]

        for suffix in suffixes:
            if name.endswith(suffix):
                name = name[: -len(suffix)]
                break

        # Replace underscores and hyphens with spaces
        name = name.replace("_", " ").replace("-", " ")

        # Clean up multiple spaces
        while "  " in name:
            name = name.replace("  ", " ")

        return name.strip()

    def add_manual_device(
        self,
        device_id: str,
        name: str,
        ip_address: str,
        device_type: str = "unknown",
        port: int = 0,
    ) -> DiscoveryResult:
        """Manually add a device to the discovered list.

        Args:
            device_id: Unique identifier
            name: Device name
            ip_address: IP address
            device_type: Type of device
            port: Port number

        Returns:
            The created DiscoveryResult
        """
        result = DiscoveryResult(
            device_id=f"manual:{device_id}",
            name=name,
            ip_address=ip_address,
            port=port,
            device_type=device_type,
            source="manual",
        )

        self._discovered[result.device_id] = result

        # Notify callbacks
        for callback in self._on_device_found:
            try:
                callback(result)
            except Exception as e:
                logger.error(f"Error in device found callback: {e}")

        return result

    def clear(self) -> None:
        """Clear all discovered devices."""
        self._discovered.clear()
