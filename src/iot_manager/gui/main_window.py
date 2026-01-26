"""Main application window."""

import customtkinter as ctk
from typing import TYPE_CHECKING, Callable, Optional
import logging

from .components.device_list import DeviceList
from .dialogs.device_settings import DeviceSettingsDialog
from .dialogs.room_manager import RoomManagerDialog
from .settings_dialog import SettingsDialog
from ..devices.base import BaseDevice
from ..i18n import _

if TYPE_CHECKING:
    from ..app import IoTManagerApp

logger = logging.getLogger(__name__)


class MainWindow(ctk.CTk):
    """Main application window."""

    def __init__(
        self,
        app: "IoTManagerApp",
        on_close: Optional[Callable] = None,
        **kwargs,
    ):
        """Initialize the main window.

        Args:
            app: The main application instance
            on_close: Callback when window is closed
            **kwargs: Additional arguments for CTk
        """
        super().__init__(**kwargs)

        self.app = app
        self._on_close = on_close
        self._rooms: list[str] = []  # List of room names
        self._device_rooms: dict[str, str] = {}  # device_id -> room name
        self._device_names: dict[str, str] = {}  # device_id -> custom name

        # Load saved device configurations
        self._load_device_config()

        self._setup_window()
        self._setup_ui()
        self._bind_events()

    def _setup_window(self) -> None:
        """Configure the window."""
        self.title(_("app_title"))

        # Set window size from settings
        settings = self.app.settings.load()
        width = settings.window_width
        height = settings.window_height

        # Center window on screen
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2

        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(600, 400)

        # Set window icon (if available)
        try:
            self.iconbitmap("assets/icon.ico")
        except Exception:
            pass

    def _setup_ui(self) -> None:
        """Set up the user interface."""
        # Configure grid
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Header
        self._setup_header()

        # Device list (main content)
        self.device_list = DeviceList(
            self,
            on_toggle=self._handle_device_toggle,
            on_brightness_change=self._handle_brightness_change,
            on_volume_change=self._handle_volume_change,
            on_color_change=self._handle_color_change,
            on_play=self._handle_play,
            on_pause=self._handle_pause,
            on_settings=self._handle_device_settings,
            on_tv_off=self._handle_tv_off,
            on_seek=self._handle_seek,
            on_seek_relative=self._handle_seek_relative,
        )
        self.device_list.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

        # Footer
        self._setup_footer()

    def _setup_header(self) -> None:
        """Set up the header bar."""
        header = ctk.CTkFrame(self, height=50, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(1, weight=1)

        # Title
        title = ctk.CTkLabel(
            header,
            text=_("app_title"),
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title.grid(row=0, column=0, padx=15, pady=10)

        # Filter dropdown
        self._current_filter = _("filter_all")
        self.filter_var = ctk.StringVar(value=_("filter_all"))
        self.filter_dropdown = ctk.CTkOptionMenu(
            header,
            variable=self.filter_var,
            values=[_("filter_all")],
            command=self._handle_filter_change,
            width=150,
        )
        self.filter_dropdown.grid(row=0, column=1, padx=10, pady=10)

        # Rooms button
        rooms_btn = ctk.CTkButton(
            header,
            text="\U0001F3E0",  # House icon
            width=40,
            command=self._show_room_manager,
        )
        rooms_btn.grid(row=0, column=2, padx=5, pady=10)

        # Settings button
        settings_btn = ctk.CTkButton(
            header,
            text="\U00002699",  # Gear icon
            width=40,
            command=self._show_settings,
        )
        settings_btn.grid(row=0, column=3, padx=5, pady=10)

        # Theme toggle
        self.theme_btn = ctk.CTkButton(
            header,
            text="\U0001F319",  # Moon icon
            width=40,
            command=self._toggle_theme,
        )
        self.theme_btn.grid(row=0, column=4, padx=(0, 15), pady=10)

    def _setup_footer(self) -> None:
        """Set up the footer/status bar."""
        footer = ctk.CTkFrame(self, height=30, corner_radius=0)
        footer.grid(row=2, column=0, sticky="ew")
        footer.grid_columnconfigure(0, weight=1)

        # Status label
        self.status_label = ctk.CTkLabel(
            footer,
            text=_("searching_devices"),
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        self.status_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")

        # Device count
        self.count_label = ctk.CTkLabel(
            footer,
            text=_("device_count_many", count=0),
            font=ctk.CTkFont(size=11),
            text_color="gray",
        )
        self.count_label.grid(row=0, column=1, padx=10, pady=5, sticky="e")

        # Refresh button
        refresh_btn = ctk.CTkButton(
            footer,
            text="\U0001F504",  # Refresh icon
            width=30,
            height=24,
            command=self._refresh_devices,
        )
        refresh_btn.grid(row=0, column=2, padx=(0, 10), pady=5)

    def _bind_events(self) -> None:
        """Bind window events."""
        self.protocol("WM_DELETE_WINDOW", self._handle_close)

    def _handle_close(self) -> None:
        """Handle window close event."""
        # Save window size
        width = self.winfo_width()
        height = self.winfo_height()
        self.app.settings.update(window_width=width, window_height=height)

        if self._on_close:
            self._on_close()
        else:
            self.destroy()

    def _handle_device_toggle(self, device: BaseDevice) -> None:
        """Handle device power toggle.

        Args:
            device: The device to toggle
        """
        logger.info(f"Toggling device: {device.name}")

        async def do_toggle():
            try:
                await device.toggle()
                await device.refresh_state()
            except Exception as e:
                logger.error(f"Failed to toggle {device.name}: {e}")

        self.app.async_bridge.run_async_with_gui_callback(
            do_toggle(),
            self.after,
            callback=lambda _: self.device_list.refresh_device(device.device_id),
        )

    def _handle_brightness_change(self, device: BaseDevice, level: int) -> None:
        """Handle device brightness change.

        Args:
            device: The device to adjust
            level: New brightness level (0-100)
        """
        logger.debug(f"Setting brightness for {device.name} to {level}%")

        async def do_brightness():
            try:
                await device.set_brightness(level)
            except Exception as e:
                logger.error(f"Failed to set brightness for {device.name}: {e}")

        self.app.async_bridge.run_async(do_brightness())

    def _handle_volume_change(self, device: BaseDevice, level: int) -> None:
        """Handle device volume change.

        Args:
            device: The device to adjust
            level: New volume level (0-100)
        """
        logger.debug(f"Setting volume for {device.name} to {level}%")

        async def do_volume():
            try:
                await device.set_volume(level)
            except Exception as e:
                logger.error(f"Failed to set volume for {device.name}: {e}")

        self.app.async_bridge.run_async(do_volume())

    def _handle_color_change(self, device: BaseDevice, rgb: tuple[int, int, int]) -> None:
        """Handle device color change.

        Args:
            device: The device to adjust
            rgb: New RGB color (r, g, b) each 0-255
        """
        logger.info(f"Setting color for {device.name} to RGB{rgb}")

        async def do_color():
            try:
                await device.set_rgb(rgb[0], rgb[1], rgb[2])
            except Exception as e:
                logger.error(f"Failed to set color for {device.name}: {e}")

        self.app.async_bridge.run_async(do_color())

    def _handle_play(self, device: BaseDevice) -> None:
        """Handle play button click.

        Args:
            device: The device to play
        """
        logger.info(f"Play on {device.name}")

        async def do_play():
            try:
                await device.play()
            except Exception as e:
                logger.error(f"Failed to play on {device.name}: {e}")

        self.app.async_bridge.run_async(do_play())

    def _handle_pause(self, device: BaseDevice) -> None:
        """Handle pause button click.

        Args:
            device: The device to pause
        """
        logger.info(f"Pause on {device.name}")

        async def do_pause():
            try:
                await device.pause()
            except Exception as e:
                logger.error(f"Failed to pause on {device.name}: {e}")

        self.app.async_bridge.run_async(do_pause())

    def _handle_tv_off(self, device: BaseDevice) -> None:
        """Handle TV off button click.

        Args:
            device: The Chromecast device
        """
        logger.info(f"TV off request for {device.name}")

        async def do_tv_off():
            try:
                await device.turn_off_tv()
            except Exception as e:
                logger.error(f"Failed to turn off TV via {device.name}: {e}")

        self.app.async_bridge.run_async(do_tv_off())

    def _handle_seek(self, device: BaseDevice, position: float) -> None:
        """Handle seek to absolute position.

        Args:
            device: The device to seek
            position: Position in seconds
        """
        logger.info(f"Seek to {position:.1f}s on {device.name}")

        async def do_seek():
            try:
                await device.seek(position)
            except Exception as e:
                logger.error(f"Failed to seek on {device.name}: {e}")

        self.app.async_bridge.run_async(do_seek())

    def _handle_seek_relative(self, device: BaseDevice, offset: float) -> None:
        """Handle relative seek (skip forward/backward).

        Args:
            device: The device to seek
            offset: Offset in seconds (positive = forward, negative = backward)
        """
        logger.info(f"Seek {offset:+.1f}s on {device.name}")

        async def do_seek():
            try:
                await device.seek_relative(offset)
            except Exception as e:
                logger.error(f"Failed to seek on {device.name}: {e}")

        self.app.async_bridge.run_async(do_seek())

    def _handle_device_settings(self, device: BaseDevice) -> None:
        """Handle device settings button click.

        Args:
            device: The device to configure
        """
        logger.info(f"Opening settings for: {device.name}")

        current_room = self._device_rooms.get(device.device_id)

        dialog = DeviceSettingsDialog(
            self,
            device=device,
            rooms=self._rooms,
            current_room=current_room,
            on_save=lambda name, room: self._save_device_settings(device, name, room),
            on_delete=lambda: self._delete_device(device),
        )

    def _save_device_settings(self, device: BaseDevice, name: str, room: Optional[str]) -> None:
        """Save device settings (name and room).

        Args:
            device: The device
            name: New name for the device
            room: Room assignment (or None)
        """
        # Update device name
        device.name = name
        self._device_names[device.device_id] = name

        # Update room
        if room:
            self._device_rooms[device.device_id] = room
            if room not in self._rooms:
                self._rooms.append(room)
                self._rooms.sort()
        elif device.device_id in self._device_rooms:
            del self._device_rooms[device.device_id]

        # Update UI
        self.device_list.update_device(device, room)

        # Save to storage
        self._save_device_config()

        # Update filter options
        self._update_filter_options()

        logger.info(f"Saved settings for {device.device_id}: name={name}, room={room}")

    def _delete_device(self, device: BaseDevice) -> None:
        """Remove a device from the list.

        Args:
            device: The device to remove
        """
        device_id = device.device_id

        # Remove from tracking
        self._device_names.pop(device_id, None)
        self._device_rooms.pop(device_id, None)

        # Remove from UI
        self.device_list.remove_device(device_id)
        self._update_device_count()

        # Save to storage
        self._save_device_config()

        logger.info(f"Deleted device: {device_id}")

    def _show_room_manager(self) -> None:
        """Show the room manager dialog."""
        logger.info("Opening room manager")

        RoomManagerDialog(
            self,
            rooms=self._rooms,
            on_rooms_changed=self._handle_rooms_changed,
        )

    def _handle_rooms_changed(self, rooms: list[str]) -> None:
        """Handle rooms being modified.

        Args:
            rooms: Updated list of rooms
        """
        self._rooms = rooms
        self._save_device_config()
        logger.info(f"Rooms updated: {rooms}")

    def _show_settings(self) -> None:
        """Show the application settings dialog."""
        logger.info("Opening settings")

        SettingsDialog(
            self,
            settings_manager=self.app.settings,
            on_save=self._handle_settings_saved,
        )

    def _handle_settings_saved(self, settings) -> None:
        """Handle settings being saved.

        Args:
            settings: The updated settings
        """
        logger.info("Settings saved, some changes may require restart")
        self.set_status(_("settings_saved"))

    def _load_device_config(self) -> None:
        """Load device configuration from storage."""
        devices = self.app.settings.load_devices()

        for device in devices:
            device_id = device.get("id")
            if device_id:
                if "name" in device:
                    self._device_names[device_id] = device["name"]
                if "room" in device:
                    self._device_rooms[device_id] = device["room"]

        # Load rooms
        settings = self.app.settings.load()
        if hasattr(settings, "rooms"):
            self._rooms = settings.rooms
        else:
            # Extract unique rooms from device configs
            self._rooms = list(set(self._device_rooms.values()))
            self._rooms.sort()

        # Update filter options after loading
        self.after(100, self._update_filter_options)

    def _save_device_config(self) -> None:
        """Save device configuration to storage."""
        devices = []

        # Combine names and rooms
        all_device_ids = set(self._device_names.keys()) | set(self._device_rooms.keys())

        for device_id in all_device_ids:
            config = {"id": device_id}
            if device_id in self._device_names:
                config["name"] = self._device_names[device_id]
            if device_id in self._device_rooms:
                config["room"] = self._device_rooms[device_id]
            devices.append(config)

        self.app.settings.save_devices(devices)

    def _toggle_theme(self) -> None:
        """Toggle between light and dark theme."""
        current = ctk.get_appearance_mode()
        new_theme = "Light" if current == "Dark" else "Dark"

        ctk.set_appearance_mode(new_theme)
        self.app.settings.update(theme=new_theme.lower())

        # Update theme button icon
        if new_theme == "Dark":
            self.theme_btn.configure(text="\U0001F319")  # Moon
        else:
            self.theme_btn.configure(text="\U00002600")  # Sun

    def _update_filter_options(self) -> None:
        """Update the filter dropdown with available options."""
        options = [_("filter_all"), _("filter_groups")]

        # Add rooms if any exist
        if self._rooms:
            for room in self._rooms:
                options.append(room)

        self.filter_dropdown.configure(values=options)

    def _handle_filter_change(self, value: str) -> None:
        """Handle filter selection change.

        Args:
            value: The selected filter value
        """
        self._current_filter = value
        self._apply_filter()

        # Scroll to top when filter changes
        self.device_list._parent_canvas.yview_moveto(0)

    def _apply_filter(self) -> None:
        """Apply the current filter to show/hide devices."""
        filter_value = self._current_filter

        for device_id, card in self.device_list._cards.items():
            device = self.device_list._devices.get(device_id)
            room = self._device_rooms.get(device_id)
            should_show = True

            if filter_value == _("filter_all"):
                should_show = True
            elif filter_value == _("filter_groups"):
                # Show only speaker groups
                should_show = hasattr(device, 'is_group') and device.is_group
            else:
                # Assume it's a room name
                should_show = room == filter_value

            if should_show:
                card.grid()
            else:
                card.grid_remove()

        # Reorder visible cards
        self._reorder_visible_cards()

    def _reorder_visible_cards(self) -> None:
        """Reorder visible cards after filtering."""
        row = 0
        for card in self.device_list._cards.values():
            if card.winfo_ismapped():
                card.grid(row=row, column=0, sticky="ew", pady=5, padx=5)
                row += 1

    def _refresh_devices(self) -> None:
        """Refresh device discovery."""
        logger.info("Refreshing device discovery")
        self.set_status(_("searching_devices"))

        async def do_refresh():
            await self.app.discovery.stop()
            await self.app.discovery.start()

        self.app.async_bridge.run_async(do_refresh())

    def add_device(self, device: BaseDevice) -> None:
        """Add a device to the display.

        Args:
            device: The device to add
        """
        # Apply saved name if available
        if device.device_id in self._device_names:
            device.name = self._device_names[device.device_id]

        # Get room assignment
        room = self._device_rooms.get(device.device_id)

        self.device_list.add_device(device, room)
        self._update_device_count()

    def remove_device(self, device_id: str) -> None:
        """Remove a device from the display.

        Args:
            device_id: ID of the device to remove
        """
        self.device_list.remove_device(device_id)
        self._update_device_count()

    def update_device(self, device: BaseDevice) -> None:
        """Update a device in the display.

        Args:
            device: The device with updated state
        """
        self.device_list.update_device(device)

    def set_status(self, message: str) -> None:
        """Set the status bar message.

        Args:
            message: The status message to display
        """
        self.status_label.configure(text=message)

    def _update_device_count(self) -> None:
        """Update the device count label."""
        count = len(self.device_list)
        if count == 1:
            text = _("device_count_one")
        else:
            text = _("device_count_many", count=count)
        self.count_label.configure(text=text)

    def minimize_to_tray(self) -> None:
        """Minimize the window to system tray."""
        self.withdraw()

    def restore_from_tray(self) -> None:
        """Restore the window from system tray."""
        self.deiconify()
        self.lift()
        self.focus_force()

    def schedule(self, callback: Callable, delay_ms: int = 0) -> str:
        """Schedule a callback to run on the GUI thread.

        Args:
            callback: Function to call
            delay_ms: Delay in milliseconds

        Returns:
            The after ID
        """
        return self.after(delay_ms, callback)
