"""Base device abstraction layer."""

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)


class DeviceType(Enum):
    """Types of IoT devices."""

    LIGHT = "light"
    SWITCH = "switch"
    PLUG = "plug"
    SENSOR = "sensor"
    THERMOSTAT = "thermostat"
    SPEAKER = "speaker"
    CAMERA = "camera"
    UNKNOWN = "unknown"


class DeviceCapability(Enum):
    """Capabilities that devices can have."""

    ON_OFF = "on_off"
    BRIGHTNESS = "brightness"
    COLOR_TEMP = "color_temp"
    RGB_COLOR = "rgb_color"
    TEMPERATURE_SENSOR = "temperature_sensor"
    HUMIDITY_SENSOR = "humidity_sensor"
    POWER_MONITORING = "power_monitoring"
    VOLUME = "volume"
    PLAYBACK = "playback"
    SEEK = "seek"


class PlaybackState(Enum):
    """Playback states for media devices."""

    UNKNOWN = "unknown"
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    BUFFERING = "buffering"


@dataclass
class DeviceState:
    """Current state of a device."""

    is_online: bool = False
    is_on: Optional[bool] = None
    brightness: Optional[int] = None  # 0-100
    color_temp: Optional[int] = None  # Kelvin (2700-6500 typical)
    rgb: Optional[tuple[int, int, int]] = None  # (R, G, B) each 0-255
    temperature: Optional[float] = None  # Celsius
    humidity: Optional[float] = None  # Percentage
    power_watts: Optional[float] = None
    volume: Optional[int] = None  # 0-100
    playback_state: PlaybackState = PlaybackState.UNKNOWN
    media_title: Optional[str] = None
    media_artist: Optional[str] = None
    media_duration: Optional[float] = None  # Duration in seconds
    media_position: Optional[float] = None  # Current position in seconds
    extra: dict = field(default_factory=dict)  # Device-specific data


class BaseDevice(ABC):
    """Abstract base class for all IoT devices.

    All device implementations should inherit from this class and
    implement the abstract methods.
    """

    def __init__(
        self,
        device_id: str,
        name: str,
        ip_address: Optional[str] = None,
        model: Optional[str] = None,
        manufacturer: Optional[str] = None,
    ):
        """Initialize a device.

        Args:
            device_id: Unique identifier for the device
            name: Human-readable name
            ip_address: IP address of the device (if known)
            model: Device model (if known)
            manufacturer: Device manufacturer (if known)
        """
        self.device_id = device_id
        self.name = name
        self.ip_address = ip_address
        self.model = model
        self.manufacturer = manufacturer
        self._state = DeviceState()

    @property
    @abstractmethod
    def device_type(self) -> DeviceType:
        """Return the device type."""
        pass

    @property
    @abstractmethod
    def capabilities(self) -> set[DeviceCapability]:
        """Return set of device capabilities."""
        pass

    @property
    def state(self) -> DeviceState:
        """Get the current device state."""
        return self._state

    @property
    def is_online(self) -> bool:
        """Check if device is online."""
        return self._state.is_online

    @property
    def is_on(self) -> Optional[bool]:
        """Check if device is on (if applicable)."""
        return self._state.is_on

    def has_capability(self, capability: DeviceCapability) -> bool:
        """Check if device has a specific capability.

        Args:
            capability: The capability to check

        Returns:
            True if device has the capability
        """
        return capability in self.capabilities

    @abstractmethod
    async def connect(self) -> bool:
        """Establish connection to the device.

        Returns:
            True if connection successful
        """
        pass

    @abstractmethod
    async def disconnect(self) -> None:
        """Disconnect from the device."""
        pass

    @abstractmethod
    async def refresh_state(self) -> DeviceState:
        """Fetch current state from the device.

        Returns:
            The updated device state
        """
        pass

    async def turn_on(self) -> bool:
        """Turn the device on.

        Returns:
            True if successful

        Raises:
            NotImplementedError: If device doesn't support on/off
        """
        if not self.has_capability(DeviceCapability.ON_OFF):
            raise NotImplementedError(f"{self.name} doesn't support on/off")
        return False

    async def turn_off(self) -> bool:
        """Turn the device off.

        Returns:
            True if successful

        Raises:
            NotImplementedError: If device doesn't support on/off
        """
        if not self.has_capability(DeviceCapability.ON_OFF):
            raise NotImplementedError(f"{self.name} doesn't support on/off")
        return False

    async def toggle(self) -> bool:
        """Toggle the device on/off state.

        Returns:
            True if successful
        """
        if self._state.is_on:
            return await self.turn_off()
        else:
            return await self.turn_on()

    async def set_brightness(self, level: int) -> bool:
        """Set brightness level.

        Args:
            level: Brightness level (0-100)

        Returns:
            True if successful

        Raises:
            NotImplementedError: If device doesn't support brightness
            ValueError: If level is out of range
        """
        if not self.has_capability(DeviceCapability.BRIGHTNESS):
            raise NotImplementedError(f"{self.name} doesn't support brightness")

        if not 0 <= level <= 100:
            raise ValueError("Brightness must be between 0 and 100")

        return False

    async def set_color_temp(self, kelvin: int) -> bool:
        """Set color temperature.

        Args:
            kelvin: Color temperature in Kelvin (typically 2700-6500)

        Returns:
            True if successful

        Raises:
            NotImplementedError: If device doesn't support color temperature
        """
        if not self.has_capability(DeviceCapability.COLOR_TEMP):
            raise NotImplementedError(f"{self.name} doesn't support color temperature")

        return False

    async def set_rgb(self, r: int, g: int, b: int) -> bool:
        """Set RGB color.

        Args:
            r: Red component (0-255)
            g: Green component (0-255)
            b: Blue component (0-255)

        Returns:
            True if successful

        Raises:
            NotImplementedError: If device doesn't support RGB color
            ValueError: If any component is out of range
        """
        if not self.has_capability(DeviceCapability.RGB_COLOR):
            raise NotImplementedError(f"{self.name} doesn't support RGB color")

        if not all(0 <= c <= 255 for c in (r, g, b)):
            raise ValueError("RGB values must be between 0 and 255")

        return False

    async def set_volume(self, level: int) -> bool:
        """Set volume level.

        Args:
            level: Volume level (0-100)

        Returns:
            True if successful

        Raises:
            NotImplementedError: If device doesn't support volume
            ValueError: If level is out of range
        """
        if not self.has_capability(DeviceCapability.VOLUME):
            raise NotImplementedError(f"{self.name} doesn't support volume")

        if not 0 <= level <= 100:
            raise ValueError("Volume must be between 0 and 100")

        return False

    async def play(self) -> bool:
        """Start/resume playback.

        Returns:
            True if successful

        Raises:
            NotImplementedError: If device doesn't support playback
        """
        if not self.has_capability(DeviceCapability.PLAYBACK):
            raise NotImplementedError(f"{self.name} doesn't support playback")
        return False

    async def pause(self) -> bool:
        """Pause playback.

        Returns:
            True if successful

        Raises:
            NotImplementedError: If device doesn't support playback
        """
        if not self.has_capability(DeviceCapability.PLAYBACK):
            raise NotImplementedError(f"{self.name} doesn't support playback")
        return False

    async def stop(self) -> bool:
        """Stop playback.

        Returns:
            True if successful

        Raises:
            NotImplementedError: If device doesn't support playback
        """
        if not self.has_capability(DeviceCapability.PLAYBACK):
            raise NotImplementedError(f"{self.name} doesn't support playback")
        return False

    async def seek(self, position: float) -> bool:
        """Seek to a position in the current media.

        Args:
            position: Position in seconds

        Returns:
            True if successful

        Raises:
            NotImplementedError: If device doesn't support seek
        """
        if not self.has_capability(DeviceCapability.SEEK):
            raise NotImplementedError(f"{self.name} doesn't support seek")
        return False

    async def seek_relative(self, offset: float) -> bool:
        """Seek relative to current position.

        Args:
            offset: Offset in seconds (positive = forward, negative = backward)

        Returns:
            True if successful

        Raises:
            NotImplementedError: If device doesn't support seek
        """
        if not self.has_capability(DeviceCapability.SEEK):
            raise NotImplementedError(f"{self.name} doesn't support seek")
        return False

    def to_dict(self) -> dict[str, Any]:
        """Convert device to a dictionary for serialization.

        Returns:
            Dictionary representation of the device
        """
        return {
            "id": self.device_id,
            "name": self.name,
            "ip_address": self.ip_address,
            "model": self.model,
            "manufacturer": self.manufacturer,
            "type": self.device_type.value,
            "capabilities": [c.value for c in self.capabilities],
            "state": {
                "is_online": self._state.is_online,
                "is_on": self._state.is_on,
                "brightness": self._state.brightness,
                "color_temp": self._state.color_temp,
                "rgb": self._state.rgb,
            },
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.device_id} name={self.name}>"
