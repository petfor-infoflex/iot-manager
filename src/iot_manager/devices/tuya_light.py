"""Tuya/Deltaco smart light implementation using tinytuya."""

from typing import Optional, Callable
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

from .base import BaseDevice, DeviceState, DeviceType, DeviceCapability

logger = logging.getLogger(__name__)

try:
    import tinytuya

    TINYTUYA_AVAILABLE = True
except ImportError:
    TINYTUYA_AVAILABLE = False
    logger.warning("tinytuya not installed - Tuya/Deltaco lights will not be available")


class TuyaLightDevice(BaseDevice):
    """Tuya/Deltaco smart light implementation using tinytuya."""

    def __init__(
        self,
        device_id: str,
        name: str,
        ip_address: str,
        local_key: str,
        tuya_id: str,
        version: float = 3.3,
    ):
        super().__init__(
            device_id=device_id,
            name=name,
            ip_address=ip_address,
            model="Tuya Light",
            manufacturer="Tuya",
        )
        self._local_key = local_key
        self._tuya_id = tuya_id
        self._version = version
        self._device: Optional[object] = None
        self._on_state_changed: Optional[Callable] = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._state.is_online = False
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

    def _run_sync(self, func):
        """Run a synchronous function in executor."""
        loop = asyncio.get_event_loop()
        return loop.run_in_executor(self._executor, func)

    async def connect(self) -> bool:
        """Connect to the Tuya bulb."""
        if not TINYTUYA_AVAILABLE:
            return False

        try:
            def do_connect():
                self._device = tinytuya.BulbDevice(
                    dev_id=self._tuya_id,
                    address=self.ip_address,
                    local_key=self._local_key,
                    version=self._version,
                )
                self._device.set_socketPersistent(True)
                return self._device.status()

            status = await self._run_sync(do_connect)

            if status and 'dps' in status:
                self._state.is_online = True
                self._parse_status(status)
                logger.info(f"Connected to Tuya light: {self.name} at {self.ip_address}")
                return True
            else:
                logger.warning(f"Failed to get status from {self.name}: {status}")
                self._state.is_online = False
                return False

        except Exception as e:
            logger.error(f"Failed to connect to Tuya light {self.name}: {e}")
            self._state.is_online = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from the bulb."""
        if self._device:
            try:
                self._device.close()
            except Exception:
                pass
        self._device = None

    def _parse_status(self, status: dict) -> None:
        """Parse Tuya status response."""
        if not status or 'dps' not in status:
            return

        dps = status['dps']

        # DPS 20 is typically power on/off for bulbs
        if '20' in dps:
            self._state.is_on = dps['20']
        elif '1' in dps:
            self._state.is_on = dps['1']

        # DPS 22 is typically brightness (10-1000)
        if '22' in dps:
            # Convert from 10-1000 to 0-100
            raw_brightness = dps['22']
            self._state.brightness = max(0, min(100, int((raw_brightness - 10) / 990 * 100)))
        elif '2' in dps:
            # Some devices use 0-255
            self._state.brightness = int(dps['2'] / 255 * 100)

        # DPS 24 is typically color in hex format (HSV)
        if '24' in dps:
            try:
                color_hex = dps['24']
                # Tuya uses HHHHSSSSVVVV format (12 hex chars)
                if len(color_hex) == 12:
                    h = int(color_hex[0:4], 16)
                    s = int(color_hex[4:8], 16) / 1000
                    v = int(color_hex[8:12], 16) / 1000
                    r, g, b = self._hsv_to_rgb(h, s, v)
                    self._state.rgb = (r, g, b)
            except Exception:
                pass

    def _hsv_to_rgb(self, h: int, s: float, v: float) -> tuple[int, int, int]:
        """Convert HSV to RGB."""
        h = h % 360
        c = v * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = v - c

        if h < 60:
            r, g, b = c, x, 0
        elif h < 120:
            r, g, b = x, c, 0
        elif h < 180:
            r, g, b = 0, c, x
        elif h < 240:
            r, g, b = 0, x, c
        elif h < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x

        return (int((r + m) * 255), int((g + m) * 255), int((b + m) * 255))

    def _rgb_to_hsv(self, r: int, g: int, b: int) -> tuple[int, int, int]:
        """Convert RGB to HSV for Tuya (returns H 0-360, S 0-1000, V 0-1000)."""
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

        s = 0 if mx == 0 else (diff / mx)
        v = mx

        return (int(h), int(s * 1000), int(v * 1000))

    async def refresh_state(self) -> DeviceState:
        """Refresh the bulb state."""
        if not self._device:
            return self._state

        try:
            def do_status():
                return self._device.status()

            status = await self._run_sync(do_status)
            if status and 'dps' in status:
                self._parse_status(status)
                self._state.is_online = True
            else:
                self._state.is_online = False

        except Exception as e:
            logger.error(f"Failed to refresh state for {self.name}: {e}")
            self._state.is_online = False

        return self._state

    async def turn_on(self) -> bool:
        """Turn on the light."""
        if not self._device:
            return False

        try:
            def do_on():
                return self._device.turn_on()

            await self._run_sync(do_on)
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
            def do_off():
                return self._device.turn_off()

            await self._run_sync(do_off)
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
            def do_brightness():
                # Convert 0-100 to Tuya's 10-1000 range
                tuya_brightness = int(10 + (level / 100) * 990)
                tuya_brightness = max(10, min(1000, tuya_brightness))
                return self._device.set_brightness(tuya_brightness)

            await self._run_sync(do_brightness)
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
            def do_color():
                return self._device.set_colour(r, g, b)

            await self._run_sync(do_color)
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
            "tuya_id": self._tuya_id,
            "local_key": self._local_key,
            "version": self._version,
        })
        return data


class TuyaLightManager:
    """Manages Tuya light connections."""

    def __init__(self, on_device_found: Callable[[TuyaLightDevice], None]):
        self._on_device_found = on_device_found
        self._devices: dict[str, TuyaLightDevice] = {}
        self._running = False
        self._device_configs: list[dict] = []

    def set_device_configs(self, configs: list[dict]) -> None:
        """Set list of known Tuya device configurations.

        Each config should have: name, ip, id, key, version (optional)
        """
        self._device_configs = configs

    async def start(self) -> bool:
        """Start Tuya connections."""
        if not TINYTUYA_AVAILABLE:
            logger.warning("tinytuya not available")
            return False

        if self._running:
            return True

        self._running = True
        logger.info("Starting Tuya light connections...")

        # Connect to configured devices
        for config in self._device_configs:
            await self._connect_device(config)

        logger.info(f"Tuya connected to {len(self._devices)} lights")
        return True

    async def _connect_device(self, config: dict) -> None:
        """Connect to a Tuya device."""
        ip = config.get('ip', '')
        tuya_id = config.get('id', '')
        local_key = config.get('key', '')
        name = config.get('name', f'Tuya {ip}')
        version = config.get('version', 3.3)

        if not ip or not tuya_id or not local_key:
            logger.warning(f"Incomplete Tuya device config: {config}")
            return

        device_id = f"tuya:{tuya_id}"
        if device_id in self._devices:
            return

        device = TuyaLightDevice(
            device_id=device_id,
            name=name,
            ip_address=ip,
            local_key=local_key,
            tuya_id=tuya_id,
            version=version,
        )

        success = await device.connect()
        if success:
            self._devices[device_id] = device

            if self._on_device_found:
                self._on_device_found(device)

            logger.info(f"Found Tuya light: {name} at {ip}")
        else:
            logger.warning(f"Failed to connect to Tuya device: {name} at {ip}")

    async def add_device(self, config: dict) -> Optional[TuyaLightDevice]:
        """Manually add a Tuya device."""
        if not self._running:
            await self.start()

        await self._connect_device(config)
        device_id = f"tuya:{config.get('id', '')}"
        return self._devices.get(device_id)

    async def stop(self) -> None:
        """Stop Tuya manager."""
        self._running = False

        for device in self._devices.values():
            await device.disconnect()

        self._devices.clear()
        logger.info("Tuya manager stopped")

    @property
    def devices(self) -> list[TuyaLightDevice]:
        return list(self._devices.values())
