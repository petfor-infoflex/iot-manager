"""Chromecast/Google Cast device implementation."""

from typing import Optional, Callable
import logging
import threading
import time

from .base import BaseDevice, DeviceState, DeviceType, DeviceCapability, PlaybackState

logger = logging.getLogger(__name__)

try:
    import pychromecast
    from pychromecast import CastBrowser, SimpleCastListener
    from pychromecast.socket_client import CastStatusListener
    from pychromecast.controllers.media import MediaStatusListener

    PYCHROMECAST_AVAILABLE = True
except ImportError:
    PYCHROMECAST_AVAILABLE = False
    logger.warning("pychromecast not installed - Chromecast devices will have limited functionality")


class ChromecastStatusListener(CastStatusListener if PYCHROMECAST_AVAILABLE else object):
    """Listener for Chromecast status changes."""

    def __init__(self, device: "ChromecastDevice"):
        self.device = device

    def new_cast_status(self, status):
        """Called when cast status changes."""
        if status:
            self.device._state.volume = int(status.volume_level * 100)
            self.device._state.is_on = not status.is_stand_by
            logger.debug(f"{self.device.name}: volume={self.device._state.volume}%")

            if self.device._on_state_changed:
                self.device._on_state_changed(self.device)


class ChromecastMediaListener(MediaStatusListener if PYCHROMECAST_AVAILABLE else object):
    """Listener for media status changes."""

    def __init__(self, device: "ChromecastDevice"):
        self.device = device

    def new_media_status(self, status):
        """Called when media status changes."""
        if status:
            # Map pychromecast player state to our PlaybackState
            player_state = status.player_state
            if player_state == "PLAYING":
                self.device._state.playback_state = PlaybackState.PLAYING
            elif player_state == "PAUSED":
                self.device._state.playback_state = PlaybackState.PAUSED
            elif player_state == "BUFFERING":
                self.device._state.playback_state = PlaybackState.BUFFERING
            elif player_state == "IDLE":
                self.device._state.playback_state = PlaybackState.IDLE
            else:
                self.device._state.playback_state = PlaybackState.UNKNOWN

            # Get media info
            self.device._state.media_title = status.title
            self.device._state.media_artist = status.artist

            logger.debug(f"{self.device.name}: playback={player_state}, title={status.title}")

            if self.device._on_state_changed:
                self.device._on_state_changed(self.device)

    def load_media_failed(self, item, error_code):
        """Called when loading media fails."""
        logger.warning(f"{self.device.name}: Failed to load media - error code {error_code}")


class ChromecastDevice(BaseDevice):
    """Google Cast device implementation using pychromecast."""

    def __init__(
        self,
        device_id: str,
        name: str,
        ip_address: str,
        uuid: Optional[str] = None,
        model_name: Optional[str] = None,
        cast_type: Optional[str] = None,
        cast: Optional[object] = None,
    ):
        super().__init__(
            device_id=device_id,
            name=name,
            ip_address=ip_address,
            model=model_name,
            manufacturer="Google",
        )
        self.uuid = uuid
        self.cast_type = cast_type or "cast"
        self._cast = cast
        self._on_state_changed: Optional[Callable] = None
        self._state.is_online = True
        self._state.volume = 0
        self._state.playback_state = PlaybackState.IDLE
        self._volume_debounce_timer: Optional[threading.Timer] = None
        self._pending_volume: Optional[int] = None

        # Check if this is a speaker group
        # cast_type "group" indicates a multi-room speaker group
        self.is_group = cast_type == "group"

        # If cast object provided, initialize from it
        if self._cast:
            self._setup_cast()

    def _setup_cast(self) -> None:
        """Set up listeners on cast object."""
        if not self._cast:
            return

        self._cast.wait(timeout=5)

        # Status listener for volume/power
        status_listener = ChromecastStatusListener(self)
        self._cast.register_status_listener(status_listener)

        # Media listener for playback state
        media_listener = ChromecastMediaListener(self)
        self._cast.media_controller.register_status_listener(media_listener)

        if self._cast.status:
            self._state.volume = int(self._cast.status.volume_level * 100)
            self._state.is_on = not self._cast.status.is_stand_by

        self._state.is_online = True
        group_text = " [GRUPP]" if self.is_group else ""
        logger.info(f"Connected to Chromecast: {self.name}{group_text} (volume: {self._state.volume}%)")

    @property
    def device_type(self) -> DeviceType:
        return DeviceType.SPEAKER

    @property
    def capabilities(self) -> set[DeviceCapability]:
        return {DeviceCapability.ON_OFF, DeviceCapability.VOLUME, DeviceCapability.PLAYBACK}

    def set_state_callback(self, callback: Callable) -> None:
        self._on_state_changed = callback

    async def connect(self) -> bool:
        """Connect is handled by ChromecastManager now."""
        return self._cast is not None

    async def disconnect(self) -> None:
        if self._cast:
            try:
                self._cast.disconnect()
            except Exception:
                pass
            self._cast = None

    async def refresh_state(self) -> DeviceState:
        if self._cast and self._cast.status:
            self._state.volume = int(self._cast.status.volume_level * 100)
            self._state.is_on = not self._cast.status.is_stand_by
            self._state.is_online = True
        return self._state

    async def turn_on(self) -> bool:
        logger.info(f"Turn on {self.name} (no-op)")
        return True

    async def turn_off(self) -> bool:
        if not self._cast:
            return False
        try:
            logger.info(f"Turning off {self.name} (quit_app)...")
            self._cast.quit_app()
            logger.info(f"Turn off {self.name} completed")
            return True
        except Exception as e:
            logger.error(f"Failed to turn off {self.name}: {e}")
            return False

    async def toggle(self) -> bool:
        """Toggle Chromecast - quit app if active, otherwise no-op.

        For Chromecast, we check if there's an active app running
        rather than relying on is_on/is_stand_by state.
        """
        if not self._cast:
            return False

        # Check if there's an active app (not just backdrop)
        has_active_app = False
        if self._cast.status and self._cast.status.app_id:
            # Backdrop app_id is usually "E8C28D3C" - that's not really "active"
            has_active_app = self._cast.status.app_id != "E8C28D3C"

        logger.info(f"Toggle {self.name}: has_active_app={has_active_app}, app_id={self._cast.status.app_id if self._cast.status else None}")

        if has_active_app:
            return await self.turn_off()
        else:
            logger.info(f"{self.name}: No active app to quit")
            return True

    async def set_volume(self, level: int) -> bool:
        """Set volume with debouncing to avoid too many API calls."""
        if not self._cast:
            logger.warning(f"Cannot set volume - not connected to {self.name}")
            return False

        self._pending_volume = level

        # Cancel existing timer
        if self._volume_debounce_timer:
            self._volume_debounce_timer.cancel()

        # Set new timer - only send after 100ms of no changes
        self._volume_debounce_timer = threading.Timer(0.1, self._send_volume)
        self._volume_debounce_timer.start()

        return True

    def _send_volume(self) -> None:
        """Actually send the volume to the device."""
        if self._pending_volume is None or not self._cast:
            return

        try:
            volume = max(0.0, min(1.0, self._pending_volume / 100.0))
            self._cast.set_volume(volume)
            self._state.volume = self._pending_volume
            logger.debug(f"Set volume for {self.name} to {self._pending_volume}%")
        except Exception as e:
            logger.error(f"Failed to set volume for {self.name}: {e}")
        finally:
            self._pending_volume = None

    async def play(self) -> bool:
        """Start/resume playback."""
        if not self._cast:
            return False
        try:
            self._cast.media_controller.play()
            logger.info(f"Play on {self.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to play on {self.name}: {e}")
            return False

    async def pause(self) -> bool:
        """Pause playback."""
        if not self._cast:
            return False
        try:
            self._cast.media_controller.pause()
            logger.info(f"Pause on {self.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to pause on {self.name}: {e}")
            return False

    async def stop(self) -> bool:
        """Stop playback."""
        if not self._cast:
            return False
        try:
            self._cast.media_controller.stop()
            logger.info(f"Stop on {self.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to stop on {self.name}: {e}")
            return False

    async def turn_off_tv(self) -> bool:
        """Attempt to turn off TV via HDMI-CEC.

        Note: pychromecast doesn't have direct CEC control, but some TVs
        will turn off when the Chromecast goes to standby/quits app.
        This is an experimental feature that may not work on all TVs.
        """
        if not self._cast:
            logger.warning(f"Cannot turn off TV - not connected to {self.name}")
            return False

        try:
            logger.info(f"Attempting to turn off TV via {self.name}...")

            # First quit any active app
            self._cast.quit_app()
            logger.debug(f"{self.name}: quit_app() called")

            # Wait a moment for the app to quit
            time.sleep(0.5)

            # Try to set volume to 0 (some TVs respond to this)
            try:
                self._cast.set_volume(0)
                logger.debug(f"{self.name}: volume set to 0")
            except Exception:
                pass

            # Note: There's no direct turn_off_tv in pychromecast API
            # The CEC command "standby" is sent by Google Assistant but
            # not exposed in the public API. Some TVs will turn off when
            # the Chromecast has no active app for a while.

            logger.info(f"TV off command sent to {self.name} (CEC support varies by TV)")
            return True

        except Exception as e:
            logger.error(f"Failed to turn off TV via {self.name}: {e}")
            return False

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            "uuid": self.uuid,
            "cast_type": self.cast_type,
            "is_group": self.is_group,
        })
        return data


class ChromecastManager:
    """Manages Chromecast discovery and connections using pychromecast's CastBrowser."""

    def __init__(self, on_device_found: Callable[[ChromecastDevice], None]):
        self._on_device_found = on_device_found
        self._browser: Optional[CastBrowser] = None
        self._zconf = None
        self._devices: dict[str, ChromecastDevice] = {}
        self._running = False

    def start(self) -> bool:
        """Start Chromecast discovery."""
        if not PYCHROMECAST_AVAILABLE:
            logger.warning("pychromecast not available")
            return False

        if self._running:
            return True

        try:
            from zeroconf import Zeroconf

            self._zconf = Zeroconf()
            listener = SimpleCastListener(self._on_cast_found, self._on_cast_removed)
            self._browser = CastBrowser(listener, self._zconf)
            self._browser.start_discovery()
            self._running = True
            logger.info("Chromecast discovery started")
            return True

        except Exception as e:
            logger.error(f"Failed to start Chromecast discovery: {e}")
            return False

    def _on_cast_found(self, uuid, service_name):
        """Called when a Chromecast is found."""
        if str(uuid) in self._devices:
            return

        try:
            # Get the cast info from browser
            cast_info = self._browser.devices.get(uuid)
            if not cast_info:
                return

            # Create Chromecast connection
            cast = pychromecast.get_chromecast_from_cast_info(cast_info, self._zconf)

            device_id = f"chromecast:{uuid}"
            device = ChromecastDevice(
                device_id=device_id,
                name=cast_info.friendly_name,
                ip_address=str(cast_info.host),
                uuid=str(uuid),
                model_name=cast_info.model_name,
                cast_type=cast_info.cast_type,
                cast=cast,
            )

            self._devices[str(uuid)] = device

            # Notify callback
            if self._on_device_found:
                self._on_device_found(device)

        except Exception as e:
            logger.error(f"Failed to connect to Chromecast {service_name}: {e}")

    def _on_cast_removed(self, uuid, service_name, cast_info):
        """Called when a Chromecast is removed."""
        uuid_str = str(uuid)
        if uuid_str in self._devices:
            del self._devices[uuid_str]
            logger.info(f"Chromecast removed: {service_name}")

    def stop(self) -> None:
        """Stop Chromecast discovery."""
        if not self._running:
            return

        self._running = False

        if self._browser:
            try:
                self._browser.stop_discovery()
            except Exception:
                pass
            self._browser = None

        if self._zconf:
            try:
                self._zconf.close()
            except Exception:
                pass
            self._zconf = None

        # Disconnect all devices
        for device in self._devices.values():
            if device._cast:
                try:
                    device._cast.disconnect()
                except Exception:
                    pass

        self._devices.clear()
        logger.info("Chromecast discovery stopped")

    @property
    def devices(self) -> list[ChromecastDevice]:
        return list(self._devices.values())
