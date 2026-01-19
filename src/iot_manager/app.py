"""Main application orchestrator."""

import customtkinter as ctk
import logging
import sys

from .core.events import EventBus, Event, EventType
from .storage.settings import SettingsManager
from .utils.async_helpers import AsyncBridge
from .discovery.service import DiscoveryService, DiscoveryResult
from .devices.registry import DeviceRegistry
from .devices.base import BaseDevice, DeviceState, DeviceType, DeviceCapability
from .devices.chromecast import ChromecastDevice, ChromecastManager, PYCHROMECAST_AVAILABLE
from .devices.wiz import WizDevice, WizManager, PYWIZLIGHT_AVAILABLE
from .devices.tapo_light import TapoDevice, TapoManager, TAPO_AVAILABLE
from .devices.tuya_light import TuyaLightDevice, TuyaLightManager, TINYTUYA_AVAILABLE
from .gui.main_window import MainWindow
from .gui.system_tray import SystemTrayManager

logger = logging.getLogger(__name__)


class DiscoveredDeviceAdapter(BaseDevice):
    """Adapter to display discovered devices before full configuration."""

    def __init__(self, result: DiscoveryResult):
        super().__init__(
            device_id=result.device_id,
            name=result.name,
            ip_address=result.ip_address,
        )
        self._result = result
        self._state.is_online = True

    @property
    def device_type(self) -> DeviceType:
        type_map = {
            "hue_bridge": DeviceType.LIGHT,
            "tradfri_gateway": DeviceType.LIGHT,
            "chromecast": DeviceType.SPEAKER,
            "airplay": DeviceType.SPEAKER,
            "esphome": DeviceType.SWITCH,
            "tuya": DeviceType.LIGHT,
            "generic_http": DeviceType.UNKNOWN,
        }
        return type_map.get(self._result.device_type, DeviceType.UNKNOWN)

    @property
    def capabilities(self) -> set[DeviceCapability]:
        # Capabilities based on device type
        caps = {DeviceCapability.ON_OFF}

        if self.device_type == DeviceType.SPEAKER:
            caps.add(DeviceCapability.VOLUME)
        elif self.device_type == DeviceType.LIGHT:
            caps.add(DeviceCapability.BRIGHTNESS)

        return caps

    async def connect(self) -> bool:
        return True

    async def disconnect(self) -> None:
        pass

    async def refresh_state(self) -> DeviceState:
        return self._state


class IoTManagerApp:
    """Main application class that orchestrates all components."""

    def __init__(self):
        """Initialize the application."""
        # Set up logging
        self._setup_logging()

        logger.info("Initializing IoT Device Manager")

        # Core services
        self.event_bus = EventBus()
        self.settings = SettingsManager()
        self.async_bridge = AsyncBridge()

        # Device services
        self.registry = DeviceRegistry()
        self.discovery = DiscoveryService(self.event_bus)

        # Set up discovery callbacks
        self.discovery.on_device_found(self._handle_device_discovered)
        self.discovery.on_device_lost(self._handle_device_lost)

        # Chromecast manager (uses pychromecast's built-in discovery)
        self._chromecast_manager = None
        if PYCHROMECAST_AVAILABLE:
            self._chromecast_manager = ChromecastManager(self._handle_chromecast_found)

        # WiZ manager for Philips WiZ lights
        self._wiz_manager = None
        if PYWIZLIGHT_AVAILABLE:
            self._wiz_manager = WizManager(self._handle_wiz_found)

        # Load settings and configure appearance
        settings = self.settings.load()

        # Tapo manager for TP-Link Tapo lights
        self._tapo_manager = None
        if TAPO_AVAILABLE and settings.tapo_username and settings.tapo_password:
            self._tapo_manager = TapoManager(
                self._handle_tapo_found,
                settings.tapo_username,
                settings.tapo_password,
            )
            if settings.tapo_device_ips:
                self._tapo_manager.set_known_ips(settings.tapo_device_ips)

        # Tuya manager for Tuya/Deltaco lights
        self._tuya_manager = None
        if TINYTUYA_AVAILABLE and settings.tuya_devices:
            self._tuya_manager = TuyaLightManager(self._handle_tuya_found)
            self._tuya_manager.set_device_configs(settings.tuya_devices)

        ctk.set_appearance_mode(settings.theme)
        ctk.set_default_color_theme("blue")

        # GUI components
        self.window = MainWindow(self, on_close=self._handle_window_close)
        self.tray = SystemTrayManager(
            self,
            on_show=self._handle_tray_show,
            on_quit=self.quit,
        )

        # Subscribe to events
        self._setup_event_handlers()

    def _setup_logging(self) -> None:
        """Configure logging."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                logging.StreamHandler(sys.stdout),
            ],
        )

    def _setup_event_handlers(self) -> None:
        """Set up event subscriptions."""
        self.event_bus.subscribe(
            EventType.DEVICE_STATE_CHANGED,
            self._on_device_state_changed,
        )

    def _handle_device_discovered(self, result: DiscoveryResult) -> None:
        """Handle a newly discovered device.

        Args:
            result: The discovery result
        """
        logger.info(f"Device discovered: {result.name} at {result.ip_address}")

        # Skip Chromecast devices - they're handled by ChromecastManager
        if result.device_type == "chromecast" and PYCHROMECAST_AVAILABLE:
            logger.debug(f"Skipping mDNS Chromecast {result.name} - handled by ChromecastManager")
            return

        # Use generic adapter for other devices
        device = DiscoveredDeviceAdapter(result)

        # Add to registry
        self.registry.add_device(device)

        # Update GUI on main thread
        self.window.after(0, lambda: self._add_device_to_gui(device))

    def _handle_chromecast_found(self, device: ChromecastDevice) -> None:
        """Handle a Chromecast found by ChromecastManager.

        Args:
            device: The ChromecastDevice (already connected)
        """
        logger.info(f"Chromecast found: {device.name} at {device.ip_address}")

        # Set callback for state updates
        device.set_state_callback(self._on_chromecast_state_changed)

        # Add to registry
        self.registry.add_device(device)

        # Update GUI on main thread
        self.window.after(0, lambda: self._add_device_to_gui(device))

    def _on_chromecast_state_changed(self, device: ChromecastDevice) -> None:
        """Handle Chromecast state change.

        Args:
            device: The device that changed
        """
        # Update GUI on main thread
        self.window.after(0, lambda: self.window.device_list.refresh_device(device.device_id))

    def _handle_wiz_found(self, device: WizDevice) -> None:
        """Handle a WiZ light found by WizManager.

        Args:
            device: The WizDevice (already connected)
        """
        logger.info(f"WiZ light found: {device.name} at {device.ip_address}")

        # Set callback for state updates
        device.set_state_callback(self._on_wiz_state_changed)

        # Add to registry
        self.registry.add_device(device)

        # Update GUI on main thread
        self.window.after(0, lambda: self._add_device_to_gui(device))

    def _on_wiz_state_changed(self, device: WizDevice) -> None:
        """Handle WiZ light state change.

        Args:
            device: The device that changed
        """
        # Update GUI on main thread
        self.window.after(0, lambda: self.window.device_list.refresh_device(device.device_id))

    def _handle_tapo_found(self, device: TapoDevice) -> None:
        """Handle a Tapo light found by TapoManager.

        Args:
            device: The TapoDevice (already connected)
        """
        logger.info(f"Tapo light found: {device.name} at {device.ip_address}")

        # Set callback for state updates
        device.set_state_callback(self._on_tapo_state_changed)

        # Add to registry
        self.registry.add_device(device)

        # Update GUI on main thread
        self.window.after(0, lambda: self._add_device_to_gui(device))

    def _on_tapo_state_changed(self, device: TapoDevice) -> None:
        """Handle Tapo light state change.

        Args:
            device: The device that changed
        """
        # Update GUI on main thread
        self.window.after(0, lambda: self.window.device_list.refresh_device(device.device_id))

    def _handle_tuya_found(self, device: TuyaLightDevice) -> None:
        """Handle a Tuya light found by TuyaManager.

        Args:
            device: The TuyaLightDevice (already connected)
        """
        logger.info(f"Tuya light found: {device.name} at {device.ip_address}")

        # Set callback for state updates
        device.set_state_callback(self._on_tuya_state_changed)

        # Add to registry
        self.registry.add_device(device)

        # Update GUI on main thread
        self.window.after(0, lambda: self._add_device_to_gui(device))

    def _on_tuya_state_changed(self, device: TuyaLightDevice) -> None:
        """Handle Tuya light state change.

        Args:
            device: The device that changed
        """
        # Update GUI on main thread
        self.window.after(0, lambda: self.window.device_list.refresh_device(device.device_id))

    def _handle_device_lost(self, device_id: str) -> None:
        """Handle a device being lost/removed.

        Args:
            device_id: The device ID
        """
        logger.info(f"Device lost: {device_id}")

        # Remove from registry
        self.registry.remove_device(device_id)

        # Update GUI on main thread
        self.window.after(0, lambda: self.window.remove_device(device_id))

    def _add_device_to_gui(self, device: BaseDevice) -> None:
        """Add a device to the GUI.

        Args:
            device: The device to add
        """
        self.window.add_device(device)
        self.window.set_status(f"Hittade: {device.name}")

    def _on_device_state_changed(self, event: Event) -> None:
        """Handle device state change event.

        Args:
            event: The event with device data
        """
        device = event.data
        if device:
            self.window.after(0, lambda: self.window.update_device(device))

    def _handle_window_close(self) -> None:
        """Handle window close - minimize to tray or quit."""
        settings = self.settings.load()

        # If system tray is available, minimize to tray
        if self.tray.is_available:
            self.tray.minimize()
        else:
            self.quit()

    def _handle_tray_show(self) -> None:
        """Handle tray show action."""
        self.window.restore_from_tray()

    def run(self) -> None:
        """Start the application."""
        logger.info("Starting IoT Device Manager")

        # Start async bridge
        self.async_bridge.start()

        # Start system tray
        if self.tray.is_available:
            self.tray.start()

        # Start discovery
        settings = self.settings.load()
        if settings.auto_discover:
            self.async_bridge.run_async(self.discovery.start())
            # Start Chromecast discovery (uses pychromecast's CastBrowser)
            if self._chromecast_manager:
                self._chromecast_manager.start()
            # Start WiZ discovery
            if self._wiz_manager:
                self.async_bridge.run_async(self._wiz_manager.start())
            # Start Tapo discovery
            if self._tapo_manager:
                self.async_bridge.run_async(self._tapo_manager.start())
            # Start Tuya connections
            if self._tuya_manager:
                self.async_bridge.run_async(self._tuya_manager.start())

        # Check if should start minimized
        if settings.start_minimized and self.tray.is_available:
            self.tray.minimize()
        else:
            # Run the main window
            self.window.mainloop()

        # Clean up after window closes
        self._cleanup()

    def _cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Cleaning up...")

        # Stop Chromecast discovery in a thread to avoid blocking
        if self._chromecast_manager:
            try:
                import threading
                def stop_chromecast():
                    try:
                        self._chromecast_manager.stop()
                    except Exception as e:
                        logger.error(f"Error stopping Chromecast manager: {e}")

                thread = threading.Thread(target=stop_chromecast, daemon=True)
                thread.start()
                thread.join(timeout=2)  # Wait max 2 seconds
            except Exception as e:
                logger.error(f"Error during Chromecast cleanup: {e}")

        # Stop WiZ discovery
        if self._wiz_manager:
            try:
                self.async_bridge.run_async(self._wiz_manager.stop())
            except Exception as e:
                logger.error(f"Error stopping WiZ manager: {e}")

        # Stop Tapo manager
        if self._tapo_manager:
            try:
                self.async_bridge.run_async(self._tapo_manager.stop())
            except Exception as e:
                logger.error(f"Error stopping Tapo manager: {e}")

        # Stop Tuya manager
        if self._tuya_manager:
            try:
                self.async_bridge.run_async(self._tuya_manager.stop())
            except Exception as e:
                logger.error(f"Error stopping Tuya manager: {e}")

        # Stop discovery (fire and forget since we're shutting down)
        if self.async_bridge.is_running:
            try:
                self.async_bridge.run_async(self.discovery.stop())
            except Exception as e:
                logger.error(f"Error stopping discovery: {e}")

        # Stop async bridge
        try:
            self.async_bridge.stop()
        except Exception as e:
            logger.error(f"Error stopping async bridge: {e}")

        # Stop tray
        try:
            self.tray.stop()
        except Exception as e:
            logger.error(f"Error stopping tray: {e}")

    def quit(self) -> None:
        """Quit the application."""
        logger.info("Quitting application")

        self._cleanup()

        try:
            self.window.quit()  # Stop mainloop
            self.window.destroy()
        except Exception as e:
            logger.error(f"Error destroying window: {e}")

        # Force exit if still hanging
        sys.exit(0)


def main():
    """Application entry point."""
    app = IoTManagerApp()
    app.run()


if __name__ == "__main__":
    main()
