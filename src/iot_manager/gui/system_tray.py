"""System tray integration using pystray."""

import threading
from typing import TYPE_CHECKING, Optional, Callable
import logging

logger = logging.getLogger(__name__)

try:
    import pystray
    from PIL import Image, ImageDraw

    PYSTRAY_AVAILABLE = True
except ImportError:
    PYSTRAY_AVAILABLE = False
    logger.warning("pystray or Pillow not installed - system tray will not be available")

if TYPE_CHECKING:
    from ..app import IoTManagerApp


def create_default_icon(size: int = 64) -> "Image.Image":
    """Create a default icon for the system tray.

    Args:
        size: Icon size in pixels

    Returns:
        A PIL Image
    """
    # Create a simple colored icon
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    # Draw a rounded square background
    margin = size // 8
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=size // 4,
        fill=(66, 133, 244, 255),  # Google blue
    )

    # Draw a simple house/home shape
    center_x = size // 2
    center_y = size // 2

    # Roof (triangle)
    roof_top = size // 4
    roof_bottom = center_y
    roof_width = size // 3

    draw.polygon(
        [
            (center_x, roof_top),  # Top
            (center_x - roof_width, roof_bottom),  # Bottom left
            (center_x + roof_width, roof_bottom),  # Bottom right
        ],
        fill=(255, 255, 255, 255),
    )

    # House body (rectangle)
    body_top = roof_bottom - size // 16
    body_bottom = size - margin - size // 8
    body_width = size // 4

    draw.rectangle(
        [
            center_x - body_width,
            body_top,
            center_x + body_width,
            body_bottom,
        ],
        fill=(255, 255, 255, 255),
    )

    return image


class SystemTrayManager:
    """Manages the system tray icon and menu."""

    def __init__(
        self,
        app: "IoTManagerApp",
        on_show: Optional[Callable] = None,
        on_quit: Optional[Callable] = None,
    ):
        """Initialize the system tray manager.

        Args:
            app: The main application instance
            on_show: Callback when "Show" is clicked
            on_quit: Callback when "Quit" is clicked
        """
        self.app = app
        self._on_show = on_show
        self._on_quit = on_quit
        self._icon: Optional["pystray.Icon"] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False

    @property
    def is_available(self) -> bool:
        """Check if system tray is available."""
        return PYSTRAY_AVAILABLE

    @property
    def is_running(self) -> bool:
        """Check if the tray icon is running."""
        return self._running and self._icon is not None

    def start(self) -> bool:
        """Start the system tray icon.

        Returns:
            True if started successfully
        """
        if not PYSTRAY_AVAILABLE:
            logger.warning("System tray not available (pystray not installed)")
            return False

        if self._running:
            return True

        try:
            # Load or create icon
            icon_image = self._load_icon()

            # Create menu
            menu = pystray.Menu(
                pystray.MenuItem(
                    "Visa fönster",
                    self._handle_show,
                    default=True,  # Double-click action
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Sök enheter",
                    self._handle_refresh,
                ),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem(
                    "Avsluta",
                    self._handle_quit,
                ),
            )

            # Create icon
            self._icon = pystray.Icon(
                name="iot_manager",
                icon=icon_image,
                title="IoT Device Manager",
                menu=menu,
            )

            # Run in background thread
            self._running = True
            self._thread = threading.Thread(
                target=self._run_icon,
                daemon=True,
                name="SystemTray",
            )
            self._thread.start()

            logger.info("System tray started")
            return True

        except Exception as e:
            logger.error(f"Failed to start system tray: {e}")
            self._running = False
            return False

    def _run_icon(self) -> None:
        """Run the icon (called in background thread)."""
        try:
            self._icon.run()
        except Exception as e:
            logger.error(f"System tray error: {e}")
        finally:
            self._running = False

    def _load_icon(self) -> "Image.Image":
        """Load the tray icon from file or create default.

        Returns:
            The icon image
        """
        try:
            return Image.open("assets/icon.png")
        except Exception:
            logger.debug("Could not load icon.png, using default")
            return create_default_icon()

    def _handle_show(self, icon, item) -> None:
        """Handle "Show" menu item click."""
        if self._on_show:
            # Schedule on GUI thread
            self.app.window.after(0, self._on_show)
        else:
            self.app.window.after(0, self.app.window.restore_from_tray)

    def _handle_refresh(self, icon, item) -> None:
        """Handle "Refresh" menu item click."""
        async def do_refresh():
            await self.app.discovery.stop()
            await self.app.discovery.start()

        self.app.async_bridge.run_async(do_refresh())

    def _handle_quit(self, icon, item) -> None:
        """Handle "Quit" menu item click."""
        self.stop()

        if self._on_quit:
            self.app.window.after(0, self._on_quit)
        else:
            self.app.window.after(0, self.app.quit)

    def stop(self) -> None:
        """Stop the system tray icon."""
        if not self._running:
            return

        self._running = False

        if self._icon:
            try:
                self._icon.stop()
            except Exception:
                pass
            self._icon = None

        logger.info("System tray stopped")

    def show_notification(
        self,
        title: str,
        message: str,
        timeout_ms: int = 5000,
    ) -> bool:
        """Show a system notification.

        Args:
            title: Notification title
            message: Notification message
            timeout_ms: Display duration in milliseconds

        Returns:
            True if notification was shown
        """
        if not self._icon or not self._running:
            return False

        try:
            self._icon.notify(message, title)
            return True
        except Exception as e:
            logger.error(f"Failed to show notification: {e}")
            return False

    def update_icon(self, icon_path: str) -> bool:
        """Update the tray icon.

        Args:
            icon_path: Path to the new icon file

        Returns:
            True if icon was updated
        """
        if not self._icon or not self._running:
            return False

        try:
            new_icon = Image.open(icon_path)
            self._icon.icon = new_icon
            return True
        except Exception as e:
            logger.error(f"Failed to update icon: {e}")
            return False

    def update_title(self, title: str) -> None:
        """Update the tray icon tooltip title.

        Args:
            title: New tooltip title
        """
        if self._icon and self._running:
            self._icon.title = title

    def minimize(self) -> None:
        """Minimize the application to system tray."""
        if not self._running:
            self.start()

        self.app.window.minimize_to_tray()
        logger.debug("Minimized to tray")

    def restore(self) -> None:
        """Restore the application from system tray."""
        self.app.window.restore_from_tray()
        logger.debug("Restored from tray")
