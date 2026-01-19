"""mDNS/Zeroconf device discovery."""

from typing import Callable, Optional
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

try:
    from zeroconf import ServiceBrowser, ServiceListener, Zeroconf, ServiceInfo

    ZEROCONF_AVAILABLE = True
except ImportError:
    ZEROCONF_AVAILABLE = False
    logger.warning("zeroconf not installed - mDNS discovery will not be available")


@dataclass
class DiscoveredDevice:
    """Information about a discovered device."""

    service_type: str
    name: str
    ip_address: Optional[str]
    port: int
    properties: dict

    @property
    def device_type_hint(self) -> str:
        """Guess the device type based on service type."""
        service_hints = {
            "_hue._tcp.local.": "hue_bridge",
            "_tradfri._udp.local.": "tradfri_gateway",
            "_googlecast._tcp.local.": "chromecast",
            "_airplay._tcp.local.": "airplay",
            "_esphomelib._tcp.local.": "esphome",
            "_http._tcp.local.": "generic_http",
            "_tuya._tcp.local.": "tuya",
        }
        return service_hints.get(self.service_type, "unknown")


class MDNSListener(ServiceListener):
    """Listener for mDNS service discoveries."""

    def __init__(
        self,
        on_discovered: Callable[[DiscoveredDevice], None],
        on_removed: Optional[Callable[[str], None]] = None,
    ):
        """Initialize the listener.

        Args:
            on_discovered: Callback when a device is discovered
            on_removed: Callback when a device is removed
        """
        self._on_discovered = on_discovered
        self._on_removed = on_removed
        self._zeroconf: Optional[Zeroconf] = None

    def set_zeroconf(self, zc: Zeroconf) -> None:
        """Set the Zeroconf instance for info lookups."""
        self._zeroconf = zc

    def add_service(self, zc: Zeroconf, service_type: str, name: str) -> None:
        """Called when a service is discovered."""
        info = zc.get_service_info(service_type, name)
        if info:
            self._handle_service_info(service_type, name, info)

    def update_service(self, zc: Zeroconf, service_type: str, name: str) -> None:
        """Called when a service is updated."""
        info = zc.get_service_info(service_type, name)
        if info:
            self._handle_service_info(service_type, name, info)

    def remove_service(self, zc: Zeroconf, service_type: str, name: str) -> None:
        """Called when a service is removed."""
        if self._on_removed:
            self._on_removed(name)

    def _handle_service_info(
        self, service_type: str, name: str, info: "ServiceInfo"
    ) -> None:
        """Process service info and notify callback."""
        addresses = info.parsed_addresses()
        ip_address = addresses[0] if addresses else None

        # Parse properties from bytes to strings
        properties = {}
        if info.properties:
            for key, value in info.properties.items():
                key_str = key.decode("utf-8") if isinstance(key, bytes) else key
                if isinstance(value, bytes):
                    try:
                        value = value.decode("utf-8")
                    except UnicodeDecodeError:
                        value = value.hex()
                properties[key_str] = value

        device = DiscoveredDevice(
            service_type=service_type,
            name=name,
            ip_address=ip_address,
            port=info.port,
            properties=properties,
        )

        logger.debug(f"Discovered: {name} at {ip_address}:{info.port}")
        self._on_discovered(device)


class MDNSDiscovery:
    """mDNS/Zeroconf discovery service."""

    # Common IoT service types to discover
    SERVICE_TYPES = [
        "_hue._tcp.local.",  # Philips Hue
        "_tradfri._udp.local.",  # IKEA Tradfri
        "_googlecast._tcp.local.",  # Google Chromecast
        "_airplay._tcp.local.",  # Apple AirPlay
        "_esphomelib._tcp.local.",  # ESPHome devices
        "_http._tcp.local.",  # Generic HTTP services
        "_homekit._tcp.local.",  # Apple HomeKit
    ]

    def __init__(self):
        self._zeroconf: Optional[Zeroconf] = None
        self._browsers: list[ServiceBrowser] = []
        self._listener: Optional[MDNSListener] = None
        self._running = False

    @property
    def is_running(self) -> bool:
        """Check if discovery is running."""
        return self._running

    def start(
        self,
        on_discovered: Callable[[DiscoveredDevice], None],
        on_removed: Optional[Callable[[str], None]] = None,
        service_types: Optional[list[str]] = None,
    ) -> bool:
        """Start mDNS discovery.

        Args:
            on_discovered: Callback when a device is discovered
            on_removed: Callback when a device is removed
            service_types: Service types to look for (defaults to common IoT types)

        Returns:
            True if started successfully
        """
        if not ZEROCONF_AVAILABLE:
            logger.error("zeroconf not available - cannot start mDNS discovery")
            return False

        if self._running:
            logger.warning("mDNS discovery already running")
            return True

        try:
            self._zeroconf = Zeroconf()
            self._listener = MDNSListener(on_discovered, on_removed)
            self._listener.set_zeroconf(self._zeroconf)

            types_to_browse = service_types or self.SERVICE_TYPES

            for service_type in types_to_browse:
                browser = ServiceBrowser(
                    self._zeroconf, service_type, self._listener
                )
                self._browsers.append(browser)
                logger.debug(f"Started browsing for {service_type}")

            self._running = True
            logger.info(
                f"mDNS discovery started, browsing {len(types_to_browse)} service types"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to start mDNS discovery: {e}")
            self.stop()
            return False

    def stop(self) -> None:
        """Stop mDNS discovery."""
        if not self._running:
            return

        self._running = False

        for browser in self._browsers:
            try:
                browser.cancel()
            except Exception:
                pass

        self._browsers.clear()

        if self._zeroconf:
            try:
                self._zeroconf.close()
            except Exception:
                pass
            self._zeroconf = None

        logger.info("mDNS discovery stopped")
