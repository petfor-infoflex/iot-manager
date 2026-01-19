"""Tuya device implementation using tinytuya."""

from typing import Optional
import logging

from .base import BaseDevice, DeviceState, DeviceType, DeviceCapability

logger = logging.getLogger(__name__)

# Try to import tinytuya, but don't fail if not installed
try:
    import tinytuya

    TINYTUYA_AVAILABLE = True
except ImportError:
    TINYTUYA_AVAILABLE = False
    logger.warning("tinytuya not installed - Tuya devices will not be available")


class TuyaDevice(BaseDevice):
    """Tuya device implementation using local LAN control.

    Requires the device's local key which can be obtained from the Tuya IoT platform
    or using tools like tinytuya's wizard.
    """

    # Common DPS (Data Point Schema) mappings for Tuya devices
    DPS_SWITCH = "1"  # On/off for switches
    DPS_SWITCH_LED = "20"  # On/off for LED bulbs
    DPS_MODE = "21"  # Mode (white/colour/scene/music)
    DPS_BRIGHTNESS = "22"  # Brightness (10-1000)
    DPS_COLOR_TEMP = "23"  # Color temperature (0-1000)
    DPS_COLOR = "24"  # HSV color as hex string

    def __init__(
        self,
        device_id: str,
        name: str,
        ip_address: str,
        local_key: str,
        version: str = "3.3",
        device_type: str = "light",
    ):
        """Initialize a Tuya device.

        Args:
            device_id: The Tuya device ID
            name: Human-readable name
            ip_address: Local IP address of the device
            local_key: The device's local encryption key
            version: Tuya protocol version (3.1, 3.3, or 3.4)
            device_type: Type of device (light, switch, plug)
        """
        super().__init__(
            device_id=device_id,
            name=name,
            ip_address=ip_address,
            manufacturer="Tuya",
        )
        self.local_key = local_key
        self.version = version
        self._device_type_str = device_type
        self._device: Optional[object] = None
        self._dps: dict = {}

    @property
    def device_type(self) -> DeviceType:
        """Return the device type."""
        type_map = {
            "light": DeviceType.LIGHT,
            "switch": DeviceType.SWITCH,
            "plug": DeviceType.PLUG,
        }
        return type_map.get(self._device_type_str, DeviceType.UNKNOWN)

    @property
    def capabilities(self) -> set[DeviceCapability]:
        """Return set of device capabilities based on type."""
        caps = {DeviceCapability.ON_OFF}

        if self._device_type_str == "light":
            caps.add(DeviceCapability.BRIGHTNESS)
            caps.add(DeviceCapability.COLOR_TEMP)
            caps.add(DeviceCapability.RGB_COLOR)

        return caps

    async def connect(self) -> bool:
        """Establish connection to the Tuya device.

        Returns:
            True if connection successful
        """
        if not TINYTUYA_AVAILABLE:
            logger.error("tinytuya not available")
            self._state.is_online = False
            return False

        try:
            if self._device_type_str == "light":
                self._device = tinytuya.BulbDevice(
                    self.device_id, self.ip_address, self.local_key
                )
            else:
                self._device = tinytuya.OutletDevice(
                    self.device_id, self.ip_address, self.local_key
                )

            self._device.set_version(float(self.version))
            self._device.set_socketPersistent(True)

            # Test connection by getting status
            status = self._device.status()

            if status and "dps" in status:
                self._state.is_online = True
                self._dps = status["dps"]
                logger.info(f"Connected to Tuya device: {self.name}")
                return True
            else:
                self._state.is_online = False
                logger.warning(f"Failed to get status from {self.name}")
                return False

        except Exception as e:
            logger.error(f"Failed to connect to Tuya device {self.name}: {e}")
            self._state.is_online = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from the device."""
        if self._device:
            try:
                self._device.close()
            except Exception:
                pass
            self._device = None
        self._state.is_online = False

    async def refresh_state(self) -> DeviceState:
        """Fetch current state from the device.

        Returns:
            The updated device state
        """
        if not self._device:
            return self._state

        try:
            status = self._device.status()

            if status and "dps" in status:
                self._dps = status["dps"]
                self._state.is_online = True

                # Parse state based on device type
                if self._device_type_str == "light":
                    self._state.is_on = self._dps.get(self.DPS_SWITCH_LED, False)

                    # Brightness is 10-1000 in Tuya, convert to 0-100
                    raw_brightness = self._dps.get(self.DPS_BRIGHTNESS, 0)
                    self._state.brightness = max(0, min(100, int(raw_brightness / 10)))

                    # Color temp is 0-1000 in Tuya, convert to Kelvin (2700-6500)
                    raw_temp = self._dps.get(self.DPS_COLOR_TEMP, 0)
                    self._state.color_temp = int(2700 + (raw_temp / 1000) * 3800)

                else:
                    self._state.is_on = self._dps.get(self.DPS_SWITCH, False)

            else:
                self._state.is_online = False

        except Exception as e:
            logger.error(f"Failed to refresh state for {self.name}: {e}")
            self._state.is_online = False

        return self._state

    async def turn_on(self) -> bool:
        """Turn the device on."""
        if not self._device:
            return False

        try:
            if self._device_type_str == "light":
                self._device.turn_on()
            else:
                self._device.set_status(True, self.DPS_SWITCH)

            self._state.is_on = True
            return True

        except Exception as e:
            logger.error(f"Failed to turn on {self.name}: {e}")
            return False

    async def turn_off(self) -> bool:
        """Turn the device off."""
        if not self._device:
            return False

        try:
            if self._device_type_str == "light":
                self._device.turn_off()
            else:
                self._device.set_status(False, self.DPS_SWITCH)

            self._state.is_on = False
            return True

        except Exception as e:
            logger.error(f"Failed to turn off {self.name}: {e}")
            return False

    async def set_brightness(self, level: int) -> bool:
        """Set brightness level (0-100)."""
        if not self.has_capability(DeviceCapability.BRIGHTNESS):
            raise NotImplementedError(f"{self.name} doesn't support brightness")

        if not 0 <= level <= 100:
            raise ValueError("Brightness must be between 0 and 100")

        if not self._device:
            return False

        try:
            # Convert 0-100 to Tuya's 10-1000 range
            tuya_brightness = max(10, int(level * 10))
            self._device.set_brightness(tuya_brightness)
            self._state.brightness = level
            return True

        except Exception as e:
            logger.error(f"Failed to set brightness for {self.name}: {e}")
            return False

    async def set_color_temp(self, kelvin: int) -> bool:
        """Set color temperature in Kelvin."""
        if not self.has_capability(DeviceCapability.COLOR_TEMP):
            raise NotImplementedError(f"{self.name} doesn't support color temperature")

        if not self._device:
            return False

        try:
            # Convert Kelvin (2700-6500) to Tuya's 0-1000 range
            kelvin = max(2700, min(6500, kelvin))
            tuya_temp = int(((kelvin - 2700) / 3800) * 1000)
            self._device.set_colourtemp(tuya_temp)
            self._state.color_temp = kelvin
            return True

        except Exception as e:
            logger.error(f"Failed to set color temp for {self.name}: {e}")
            return False

    async def set_rgb(self, r: int, g: int, b: int) -> bool:
        """Set RGB color."""
        if not self.has_capability(DeviceCapability.RGB_COLOR):
            raise NotImplementedError(f"{self.name} doesn't support RGB color")

        if not all(0 <= c <= 255 for c in (r, g, b)):
            raise ValueError("RGB values must be between 0 and 255")

        if not self._device:
            return False

        try:
            self._device.set_colour(r, g, b)
            self._state.rgb = (r, g, b)
            return True

        except Exception as e:
            logger.error(f"Failed to set RGB for {self.name}: {e}")
            return False

    def to_dict(self) -> dict:
        """Convert device to dictionary including Tuya-specific fields."""
        data = super().to_dict()
        data.update(
            {
                "local_key": self.local_key,
                "version": self.version,
                "device_type_str": self._device_type_str,
            }
        )
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "TuyaDevice":
        """Create a TuyaDevice from a dictionary.

        Args:
            data: Dictionary with device configuration

        Returns:
            A new TuyaDevice instance
        """
        return cls(
            device_id=data["id"],
            name=data["name"],
            ip_address=data["ip_address"],
            local_key=data["local_key"],
            version=data.get("version", "3.3"),
            device_type=data.get("device_type_str", "light"),
        )
