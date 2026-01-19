"""TP-Link Tapo smart light implementation."""

from typing import Optional, Callable
import logging
import asyncio

from .base import BaseDevice, DeviceState, DeviceType, DeviceCapability

logger = logging.getLogger(__name__)

try:
    from tapo import ApiClient
    from tapo.requests import Color

    TAPO_AVAILABLE = True
except ImportError:
    TAPO_AVAILABLE = False
    logger.warning("tapo not installed - Tapo lights will not be available")


class TapoDevice(BaseDevice):
    """TP-Link Tapo smart light implementation."""

    def __init__(
        self,
        device_id: str,
        name: str,
        ip_address: str,
        model: str = "Tapo Light",
        device_handler: Optional[object] = None,
    ):
        super().__init__(
            device_id=device_id,
            name=name,
            ip_address=ip_address,
            model=model,
            manufacturer="TP-Link",
        )
        self._device = device_handler
        self._on_state_changed: Optional[Callable] = None
        self._state.is_online = True
        self._state.is_on = False
        self._state.brightness = 0
        self._supports_color = False

    @property
    def device_type(self) -> DeviceType:
        return DeviceType.LIGHT

    @property
    def capabilities(self) -> set[DeviceCapability]:
        caps = {DeviceCapability.ON_OFF, DeviceCapability.BRIGHTNESS}
        if self._supports_color:
            caps.add(DeviceCapability.RGB_COLOR)
        return caps

    def set_state_callback(self, callback: Callable) -> None:
        self._on_state_changed = callback

    def set_supports_color(self, supports: bool) -> None:
        """Set whether this device supports color."""
        self._supports_color = supports

    async def connect(self) -> bool:
        """Connect to the Tapo bulb."""
        if not TAPO_AVAILABLE or not self._device:
            return False

        try:
            await self.refresh_state()
            self._state.is_online = True
            logger.info(f"Connected to Tapo light: {self.name} at {self.ip_address}")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Tapo light {self.name}: {e}")
            self._state.is_online = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from the bulb."""
        self._device = None

    async def refresh_state(self) -> DeviceState:
        """Refresh the bulb state."""
        if not self._device:
            return self._state

        try:
            info = await self._device.get_device_info()
            self._state.is_on = info.device_on
            self._state.brightness = info.brightness if hasattr(info, 'brightness') else (100 if info.device_on else 0)
            self._state.is_online = True

            # Get color if supported
            if hasattr(info, 'hue') and hasattr(info, 'saturation'):
                # Convert HSV to RGB (simplified)
                h, s = info.hue, info.saturation
                if s > 0:
                    # Has color set
                    self._supports_color = True
                    # Store hue/saturation for later
                    self._state.extra['hue'] = h
                    self._state.extra['saturation'] = s

            if hasattr(info, 'color_temp') and info.color_temp:
                self._state.color_temp = info.color_temp

        except Exception as e:
            logger.error(f"Failed to refresh state for {self.name}: {e}")
            self._state.is_online = False

        return self._state

    async def turn_on(self) -> bool:
        """Turn on the light."""
        if not self._device:
            return False

        try:
            await self._device.on()
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
        if not self._device:
            return False

        try:
            await self._device.off()
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
        if not self._device:
            return False

        try:
            await self._device.set_brightness(level)
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
        if not self._device:
            return False

        try:
            # tapo library uses Color enum or set_hue_saturation
            # Convert RGB to HSV
            h, s, v = self._rgb_to_hsv(r, g, b)
            await self._device.set_hue_saturation(h, s)
            self._state.rgb = (r, g, b)
            self._state.is_on = True
            logger.debug(f"Set color for {self.name} to RGB({r}, {g}, {b})")

            if self._on_state_changed:
                self._on_state_changed(self)

            return True
        except Exception as e:
            logger.error(f"Failed to set color for {self.name}: {e}")
            return False

    def _rgb_to_hsv(self, r: int, g: int, b: int) -> tuple[int, int, int]:
        """Convert RGB to HSV."""
        r, g, b = r / 255.0, g / 255.0, b / 255.0
        mx = max(r, g, b)
        mn = min(r, g, b)
        diff = mx - mn

        if mx == mn:
            h = 0
        elif mx == r:
            h = (60 * ((g - b) / diff) + 360) % 360
        elif mx == g:
            h = (60 * ((b - r) / diff) + 120) % 360
        else:
            h = (60 * ((r - g) / diff) + 240) % 360

        s = 0 if mx == 0 else (diff / mx) * 100
        v = mx * 100

        return int(h), int(s), int(v)

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            "supports_color": self._supports_color,
        })
        return data


class TapoManager:
    """Manages Tapo light discovery and connections."""

    def __init__(
        self,
        on_device_found: Callable[[TapoDevice], None],
        username: str,
        password: str,
    ):
        self._on_device_found = on_device_found
        self._username = username
        self._password = password
        self._devices: dict[str, TapoDevice] = {}
        self._running = False
        self._client: Optional[ApiClient] = None
        self._known_ips: list[str] = []

    def set_known_ips(self, ips: list[str]) -> None:
        """Set list of known Tapo device IPs to connect to."""
        self._known_ips = ips

    async def start(self) -> bool:
        """Start Tapo discovery/connection."""
        if not TAPO_AVAILABLE:
            logger.warning("tapo not available")
            return False

        if self._running:
            return True

        if not self._username or not self._password:
            logger.warning("Tapo credentials not configured")
            return False

        self._running = True
        logger.info("Starting Tapo connection...")

        try:
            self._client = ApiClient(self._username, self._password)

            # Connect to known IPs
            for ip in self._known_ips:
                await self._connect_to_device(ip)

            logger.info(f"Tapo connected to {len(self._devices)} lights")
            return True

        except Exception as e:
            logger.error(f"Failed to start Tapo manager: {e}")
            return False

    async def _connect_to_device(self, ip: str) -> None:
        """Connect to a Tapo device at the given IP."""
        if not self._client:
            return

        device_id = f"tapo:{ip}"
        if device_id in self._devices:
            return

        try:
            # Try L530 (color) first, then L510 (white)
            try:
                device_handler = await self._client.l530(ip)
                supports_color = True
                model = "L530"
            except Exception:
                try:
                    device_handler = await self._client.l510(ip)
                    supports_color = False
                    model = "L510"
                except Exception:
                    # Try generic light
                    device_handler = await self._client.generic_device(ip)
                    supports_color = False
                    model = "Tapo Light"

            # Get device info for name
            info = await device_handler.get_device_info()
            name = info.nickname if hasattr(info, 'nickname') and info.nickname else f"Tapo {ip.split('.')[-1]}"

            device = TapoDevice(
                device_id=device_id,
                name=name,
                ip_address=ip,
                model=model,
                device_handler=device_handler,
            )
            device.set_supports_color(supports_color)

            # Set initial state
            device._state.is_on = info.device_on if hasattr(info, 'device_on') else False
            device._state.brightness = info.brightness if hasattr(info, 'brightness') else 0
            device._state.is_online = True

            self._devices[device_id] = device

            if self._on_device_found:
                self._on_device_found(device)

            logger.info(f"Found Tapo light: {name} ({model}) at {ip}")

        except Exception as e:
            logger.error(f"Failed to connect to Tapo device at {ip}: {e}")

    async def add_device(self, ip: str) -> Optional[TapoDevice]:
        """Manually add a Tapo device by IP."""
        if not self._running:
            await self.start()

        await self._connect_to_device(ip)
        device_id = f"tapo:{ip}"
        return self._devices.get(device_id)

    async def stop(self) -> None:
        """Stop Tapo manager."""
        self._running = False
        self._devices.clear()
        self._client = None
        logger.info("Tapo manager stopped")

    @property
    def devices(self) -> list[TapoDevice]:
        return list(self._devices.values())
