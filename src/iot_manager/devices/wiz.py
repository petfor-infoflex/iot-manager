"""Philips WiZ smart light implementation."""

from typing import Optional, Callable
import logging
import asyncio

from .base import BaseDevice, DeviceState, DeviceType, DeviceCapability

logger = logging.getLogger(__name__)

try:
    from pywizlight import wizlight, PilotBuilder, discovery
    from pywizlight.bulblibrary import BulbType

    PYWIZLIGHT_AVAILABLE = True
except ImportError:
    PYWIZLIGHT_AVAILABLE = False
    logger.warning("pywizlight not installed - WiZ lights will not be available")


class WizDevice(BaseDevice):
    """Philips WiZ smart light implementation using pywizlight."""

    def __init__(
        self,
        device_id: str,
        name: str,
        ip_address: str,
        mac: Optional[str] = None,
        bulb: Optional[object] = None,
    ):
        super().__init__(
            device_id=device_id,
            name=name,
            ip_address=ip_address,
            model="WiZ Light",
            manufacturer="Philips",
        )
        self.mac = mac
        self._bulb = bulb
        self._on_state_changed: Optional[Callable] = None
        self._state.is_online = True
        self._state.is_on = False
        self._state.brightness = 0

    @property
    def device_type(self) -> DeviceType:
        return DeviceType.LIGHT

    @property
    def capabilities(self) -> set[DeviceCapability]:
        return {DeviceCapability.ON_OFF, DeviceCapability.BRIGHTNESS, DeviceCapability.RGB_COLOR}

    def set_state_callback(self, callback: Callable) -> None:
        self._on_state_changed = callback

    async def connect(self) -> bool:
        """Connect to the WiZ bulb."""
        if not PYWIZLIGHT_AVAILABLE:
            return False

        try:
            if not self._bulb:
                self._bulb = wizlight(self.ip_address)

            # Get initial state
            await self.refresh_state()
            self._state.is_online = True
            logger.info(f"Connected to WiZ light: {self.name} at {self.ip_address}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to WiZ light {self.name}: {e}")
            self._state.is_online = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from the bulb."""
        self._bulb = None

    async def refresh_state(self) -> DeviceState:
        """Refresh the bulb state."""
        if not self._bulb:
            return self._state

        try:
            state = await self._bulb.updateState()
            if state:
                self._state.is_on = state.get_state()
                brightness = state.get_brightness()
                # WiZ brightness is 10-255, convert to 0-100
                if brightness is not None:
                    self._state.brightness = max(0, min(100, int((brightness - 10) / 245 * 100)))
                else:
                    self._state.brightness = 0 if not self._state.is_on else 100
                self._state.is_online = True

                # Get color temp if available
                color_temp = state.get_colortemp()
                if color_temp:
                    self._state.color_temp = color_temp

                # Get RGB if available
                rgb = state.get_rgb()
                if rgb and rgb != (None, None, None):
                    self._state.rgb = rgb

        except Exception as e:
            logger.error(f"Failed to refresh state for {self.name}: {e}")
            self._state.is_online = False

        return self._state

    async def turn_on(self) -> bool:
        """Turn on the light."""
        if not self._bulb:
            return False

        try:
            await self._bulb.turn_on(PilotBuilder())
            self._state.is_on = True
            logger.info(f"Turned on {self.name}")

            if self._on_state_changed:
                self._on_state_changed(self)

            return True
        except Exception as e:
            logger.error(f"Failed to turn on {self.name}: {e}")
            return False

    async def turn_off(self) -> bool:
        """Turn off the light."""
        if not self._bulb:
            return False

        try:
            await self._bulb.turn_off()
            self._state.is_on = False
            logger.info(f"Turned off {self.name}")

            if self._on_state_changed:
                self._on_state_changed(self)

            return True
        except Exception as e:
            logger.error(f"Failed to turn off {self.name}: {e}")
            return False

    async def toggle(self) -> bool:
        """Toggle the light."""
        if self._state.is_on:
            return await self.turn_off()
        else:
            return await self.turn_on()

    async def set_brightness(self, level: int) -> bool:
        """Set the brightness level (0-100)."""
        if not self._bulb:
            return False

        try:
            # Convert 0-100 to WiZ's 10-255 range
            wiz_brightness = int(10 + (level / 100) * 245)
            wiz_brightness = max(10, min(255, wiz_brightness))

            await self._bulb.turn_on(PilotBuilder(brightness=wiz_brightness))
            self._state.brightness = level
            self._state.is_on = level > 0
            logger.debug(f"Set brightness for {self.name} to {level}%")

            if self._on_state_changed:
                self._on_state_changed(self)

            return True
        except Exception as e:
            logger.error(f"Failed to set brightness for {self.name}: {e}")
            return False

    async def set_rgb(self, r: int, g: int, b: int) -> bool:
        """Set the RGB color (each 0-255)."""
        if not self._bulb:
            return False

        try:
            await self._bulb.turn_on(PilotBuilder(rgb=(r, g, b)))
            self._state.rgb = (r, g, b)
            self._state.is_on = True
            logger.debug(f"Set color for {self.name} to RGB({r}, {g}, {b})")

            if self._on_state_changed:
                self._on_state_changed(self)

            return True
        except Exception as e:
            logger.error(f"Failed to set color for {self.name}: {e}")
            return False

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            "mac": self.mac,
        })
        return data


class WizManager:
    """Manages WiZ light discovery and connections."""

    def __init__(self, on_device_found: Callable[[WizDevice], None]):
        self._on_device_found = on_device_found
        self._devices: dict[str, WizDevice] = {}
        self._running = False
        self._discovery_task: Optional[asyncio.Task] = None

    async def start(self) -> bool:
        """Start WiZ discovery."""
        if not PYWIZLIGHT_AVAILABLE:
            logger.warning("pywizlight not available")
            return False

        if self._running:
            return True

        self._running = True
        logger.info("Starting WiZ discovery...")

        try:
            # Discover WiZ bulbs on the network
            bulbs = await discovery.discover_lights(broadcast_space="192.168.1.255")

            for bulb in bulbs:
                await self._handle_bulb_found(bulb)

            logger.info(f"WiZ discovery found {len(bulbs)} lights")
            return True

        except Exception as e:
            logger.error(f"Failed to discover WiZ lights: {e}")
            return False

    async def _handle_bulb_found(self, bulb) -> None:
        """Handle a discovered WiZ bulb."""
        ip = bulb.ip
        mac = bulb.mac if hasattr(bulb, 'mac') else None

        device_id = f"wiz:{mac}" if mac else f"wiz:{ip}"

        if device_id in self._devices:
            return

        try:
            # Get bulb state to get more info
            state = await bulb.updateState()

            # Try to get a friendly name
            name = f"WiZ {ip.split('.')[-1]}"
            if hasattr(bulb, 'bulbtype') and bulb.bulbtype:
                name = f"WiZ {bulb.bulbtype.name}"

            device = WizDevice(
                device_id=device_id,
                name=name,
                ip_address=ip,
                mac=mac,
                bulb=bulb,
            )

            # Set initial state
            if state:
                device._state.is_on = state.get_state()
                brightness = state.get_brightness()
                if brightness is not None:
                    device._state.brightness = max(0, min(100, int((brightness - 10) / 245 * 100)))
                device._state.is_online = True

            self._devices[device_id] = device

            if self._on_device_found:
                self._on_device_found(device)

            logger.info(f"Found WiZ light: {name} at {ip}")

        except Exception as e:
            logger.error(f"Failed to initialize WiZ bulb at {ip}: {e}")

    async def stop(self) -> None:
        """Stop WiZ discovery."""
        self._running = False

        if self._discovery_task:
            self._discovery_task.cancel()
            try:
                await self._discovery_task
            except asyncio.CancelledError:
                pass
            self._discovery_task = None

        self._devices.clear()
        logger.info("WiZ discovery stopped")

    @property
    def devices(self) -> list[WizDevice]:
        return list(self._devices.values())
