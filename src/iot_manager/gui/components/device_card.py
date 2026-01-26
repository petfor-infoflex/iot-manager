"""Device card component for displaying and controlling a device."""

import customtkinter as ctk
from typing import Callable, Optional
import logging

from ...devices.base import BaseDevice, DeviceCapability, DeviceType, PlaybackState
from ...i18n import _

logger = logging.getLogger(__name__)


class DeviceCard(ctk.CTkFrame):
    """A card component that displays device info and controls."""

    # Device type icons (using unicode symbols)
    TYPE_ICONS = {
        DeviceType.LIGHT: "\U0001F4A1",  # Light bulb
        DeviceType.SWITCH: "\U0001F50C",  # Plug
        DeviceType.PLUG: "\U0001F50C",  # Plug
        DeviceType.SENSOR: "\U0001F321",  # Thermometer
        DeviceType.THERMOSTAT: "\U0001F321",  # Thermometer
        DeviceType.SPEAKER: "\U0001F50A",  # Speaker
        DeviceType.CAMERA: "\U0001F4F7",  # Camera
        DeviceType.UNKNOWN: "\U00002753",  # Question mark
    }

    def __init__(
        self,
        parent,
        device: BaseDevice,
        room: Optional[str] = None,
        on_toggle: Optional[Callable[[BaseDevice], None]] = None,
        on_brightness_change: Optional[Callable[[BaseDevice, int], None]] = None,
        on_volume_change: Optional[Callable[[BaseDevice, int], None]] = None,
        on_color_change: Optional[Callable[[BaseDevice, tuple[int, int, int]], None]] = None,
        on_play: Optional[Callable[[BaseDevice], None]] = None,
        on_pause: Optional[Callable[[BaseDevice], None]] = None,
        on_settings: Optional[Callable[[BaseDevice], None]] = None,
        on_tv_off: Optional[Callable[[BaseDevice], None]] = None,
        on_seek: Optional[Callable[[BaseDevice, float], None]] = None,
        on_seek_relative: Optional[Callable[[BaseDevice, float], None]] = None,
        **kwargs,
    ):
        """Initialize the device card.

        Args:
            parent: Parent widget
            device: The device to display
            room: Room the device belongs to
            on_toggle: Callback when power button is clicked
            on_brightness_change: Callback when brightness slider changes
            on_volume_change: Callback when volume slider changes
            on_color_change: Callback when color is changed (RGB tuple)
            on_play: Callback when play button is clicked
            on_pause: Callback when pause button is clicked
            on_settings: Callback when settings button is clicked
            on_tv_off: Callback when TV off button is clicked (Chromecast only)
            on_seek: Callback when seek slider is released (position in seconds)
            on_seek_relative: Callback for relative seek (+/- seconds)
            **kwargs: Additional arguments for CTkFrame
        """
        super().__init__(parent, **kwargs)

        self.device = device
        self.room = room
        self._on_toggle = on_toggle
        self._on_brightness_change = on_brightness_change
        self._on_volume_change = on_volume_change
        self._on_color_change = on_color_change
        self._on_play = on_play
        self._on_pause = on_pause
        self._on_settings = on_settings
        self._on_tv_off = on_tv_off
        self._on_seek = on_seek
        self._on_seek_relative = on_seek_relative
        self._updating = False  # Prevent feedback loops

        self._setup_ui()
        self._update_from_device()

    def _setup_ui(self) -> None:
        """Set up the card UI."""
        self.configure(corner_radius=10)

        # Main container with padding
        self.grid_columnconfigure(0, weight=1)

        # Header row: icon, name, status, power button
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 5))
        header_frame.grid_columnconfigure(1, weight=1)

        # Device type icon
        icon = self.TYPE_ICONS.get(self.device.device_type, "\U00002753")
        self.icon_label = ctk.CTkLabel(
            header_frame, text=icon, font=ctk.CTkFont(size=24)
        )
        self.icon_label.grid(row=0, column=0, padx=(0, 10))

        # Device name
        self.name_label = ctk.CTkLabel(
            header_frame,
            text=self.device.name,
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        self.name_label.grid(row=0, column=1, sticky="w")

        # Online status indicator
        self.status_indicator = ctk.CTkLabel(
            header_frame,
            text="\U000025CF",  # Filled circle
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        self.status_indicator.grid(row=0, column=2, padx=5)

        # Stop stream button (for speakers/Chromecasts)
        if self.device.has_capability(DeviceCapability.ON_OFF):
            self.power_button = ctk.CTkButton(
                header_frame,
                text="\U000023F9",  # Stop square symbol
                width=40,
                height=40,
                corner_radius=20,
                command=self._handle_toggle,
            )
            self.power_button.grid(row=0, column=3, padx=(5, 0))
        else:
            self.power_button = None

        # TV Off button (for Chromecasts connected to TV)
        self.tv_off_button = None
        if hasattr(self.device, 'cast_type') and self.device.cast_type == 'cast':
            self.tv_off_button = ctk.CTkButton(
                header_frame,
                text="\U0001F4FA",  # TV emoji
                width=40,
                height=40,
                corner_radius=20,
                fg_color=("gray70", "gray30"),
                hover_color=("red", "#c0392b"),
                command=self._handle_tv_off,
            )
            self.tv_off_button.grid(row=0, column=4, padx=(5, 0))

        # Device info row
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=2)

        self.info_label = ctk.CTkLabel(
            info_frame,
            text=self._get_info_text(),
            font=ctk.CTkFont(size=11),
            text_color="gray",
            anchor="w",
        )
        self.info_label.pack(side="left")

        # Brightness slider (if supported)
        if self.device.has_capability(DeviceCapability.BRIGHTNESS):
            self._setup_brightness_slider()

        # Color picker (if supported)
        if self.device.has_capability(DeviceCapability.RGB_COLOR):
            self._setup_color_picker()

        # Volume slider (for speakers)
        if self.device.has_capability(DeviceCapability.VOLUME):
            self._setup_volume_slider()

        # Playback controls (for speakers with media)
        if self.device.has_capability(DeviceCapability.PLAYBACK):
            self._setup_playback_controls()

        # Seek controls (for media with duration)
        if self.device.has_capability(DeviceCapability.SEEK):
            self._setup_seek_controls()

        # Settings button row
        settings_frame = ctk.CTkFrame(self, fg_color="transparent")
        settings_frame.grid(row=6, column=0, sticky="ew", padx=10, pady=(5, 10))

        self.settings_button = ctk.CTkButton(
            settings_frame,
            text="\U00002699 " + _("settings"),
            height=28,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            text_color=("gray40", "gray60"),
            command=self._handle_settings,
        )
        self.settings_button.pack(side="right")

    def _setup_brightness_slider(self) -> None:
        """Set up the brightness slider."""
        slider_frame = ctk.CTkFrame(self, fg_color="transparent")
        slider_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        slider_frame.grid_columnconfigure(1, weight=1)

        # Brightness icon
        brightness_icon = ctk.CTkLabel(
            slider_frame, text="\U00002600", font=ctk.CTkFont(size=14)  # Sun
        )
        brightness_icon.grid(row=0, column=0, padx=(0, 5))

        # Slider
        self.brightness_slider = ctk.CTkSlider(
            slider_frame,
            from_=0,
            to=100,
            number_of_steps=100,
            command=self._handle_brightness_change,
        )
        self.brightness_slider.grid(row=0, column=1, sticky="ew")

        # Value label
        self.brightness_label = ctk.CTkLabel(
            slider_frame, text="0%", width=40, font=ctk.CTkFont(size=11)
        )
        self.brightness_label.grid(row=0, column=2, padx=(5, 0))

    def _setup_color_picker(self) -> None:
        """Set up the color picker for RGB lights."""
        color_frame = ctk.CTkFrame(self, fg_color="transparent")
        color_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=5)

        # Color label
        color_label = ctk.CTkLabel(
            color_frame, text="\U0001F3A8", font=ctk.CTkFont(size=14)  # Palette
        )
        color_label.pack(side="left", padx=(0, 10))

        # Predefined colors as buttons (names not shown, just RGB values)
        self._color_buttons = []
        colors = [
            ((255, 255, 255)),    # White
            ((255, 200, 150)),    # Warm white
            ((255, 0, 0)),        # Red
            ((0, 255, 0)),        # Green
            ((0, 0, 255)),        # Blue
            ((255, 255, 0)),      # Yellow
            ((0, 255, 255)),      # Cyan
            ((255, 0, 255)),      # Magenta
            ((255, 165, 0)),      # Orange
            ((128, 0, 128)),      # Purple
        ]

        for rgb in colors:
            hex_color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
            btn = ctk.CTkButton(
                color_frame,
                text="",
                width=24,
                height=24,
                corner_radius=12,
                fg_color=hex_color,
                hover_color=hex_color,
                border_width=2,
                border_color=("gray70", "gray30"),
                command=lambda r=rgb: self._handle_color_select(r),
            )
            btn.pack(side="left", padx=2)
            self._color_buttons.append((btn, rgb))

        # Current color indicator
        self.color_indicator = ctk.CTkLabel(
            color_frame,
            text="\U000025CF",  # Filled circle
            font=ctk.CTkFont(size=20),
            text_color="white",
        )
        self.color_indicator.pack(side="right", padx=(10, 0))

    def _handle_color_select(self, rgb: tuple[int, int, int]) -> None:
        """Handle color button click."""
        if self._on_color_change:
            self._on_color_change(self.device, rgb)

        # Update indicator color
        hex_color = f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        self.color_indicator.configure(text_color=hex_color)

    def _setup_volume_slider(self) -> None:
        """Set up the volume slider for speakers."""
        slider_frame = ctk.CTkFrame(self, fg_color="transparent")
        slider_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)
        slider_frame.grid_columnconfigure(1, weight=1)

        # Volume icon
        volume_icon = ctk.CTkLabel(
            slider_frame, text="\U0001F50A", font=ctk.CTkFont(size=14)  # Speaker
        )
        volume_icon.grid(row=0, column=0, padx=(0, 5))

        # Slider - only update label while dragging
        self.volume_slider = ctk.CTkSlider(
            slider_frame,
            from_=0,
            to=100,
            number_of_steps=100,
            command=self._handle_volume_drag,
        )
        self.volume_slider.grid(row=0, column=1, sticky="ew")

        # Bind release event to actually send the volume
        self.volume_slider.bind("<ButtonRelease-1>", self._handle_volume_release)

        # Value label
        self.volume_label = ctk.CTkLabel(
            slider_frame, text="0%", width=40, font=ctk.CTkFont(size=11)
        )
        self.volume_label.grid(row=0, column=2, padx=(5, 0))

    def _handle_volume_drag(self, value: float) -> None:
        """Handle volume slider drag - only update label."""
        if self._updating:
            return

        level = int(value)
        self.volume_label.configure(text=f"{level}%")

    def _handle_volume_release(self, event) -> None:
        """Handle volume slider release - send volume to device."""
        if self._updating:
            return

        level = int(self.volume_slider.get())
        if self._on_volume_change:
            self._on_volume_change(self.device, level)

    def _setup_playback_controls(self) -> None:
        """Set up play/pause controls for media devices."""
        playback_frame = ctk.CTkFrame(self, fg_color="transparent")
        playback_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=5)

        # Media info label (title/artist)
        self.media_info_label = ctk.CTkLabel(
            playback_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="gray",
            anchor="w",
        )
        self.media_info_label.pack(side="left", fill="x", expand=True)

        # Single play/pause toggle button
        self.playback_button = ctk.CTkButton(
            playback_frame,
            text="\U000025B6",  # Play triangle (default)
            width=36,
            height=36,
            corner_radius=18,
            command=self._handle_playback_toggle,
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40"),
        )
        self.playback_button.pack(side="right", padx=2)

    def _handle_playback_toggle(self) -> None:
        """Handle play/pause button click - toggles based on current state."""
        state = self.device.state
        if state.playback_state == PlaybackState.PLAYING:
            # Currently playing, so pause
            if self._on_pause:
                self._on_pause(self.device)
        else:
            # Not playing (paused, idle, etc), so play
            if self._on_play:
                self._on_play(self.device)

    def _setup_seek_controls(self) -> None:
        """Set up seek slider and skip buttons for media devices."""
        # Container frame for all seek controls (hidden when no media)
        self.seek_container = ctk.CTkFrame(self, fg_color="transparent")
        self.seek_container.grid(row=4, column=0, sticky="ew", padx=0, pady=0)
        self.seek_container.grid_columnconfigure(0, weight=1)

        # Seek controls frame
        seek_frame = ctk.CTkFrame(self.seek_container, fg_color="transparent")
        seek_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        seek_frame.grid_columnconfigure(1, weight=1)

        # Rewind button (-10s)
        self.rewind_button = ctk.CTkButton(
            seek_frame,
            text="\U000023EA",  # Rewind symbol
            width=32,
            height=28,
            corner_radius=14,
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40"),
            command=lambda: self._handle_seek_relative(-10),
        )
        self.rewind_button.grid(row=0, column=0, padx=(0, 5))

        # Progress slider
        self.seek_slider = ctk.CTkSlider(
            seek_frame,
            from_=0,
            to=100,
            number_of_steps=100,
            command=self._handle_seek_drag,
        )
        self.seek_slider.grid(row=0, column=1, sticky="ew")
        self.seek_slider.set(0)

        # Bind release event to actually send the seek
        self.seek_slider.bind("<ButtonRelease-1>", self._handle_seek_release)

        # Fast forward button (+10s)
        self.forward_button = ctk.CTkButton(
            seek_frame,
            text="\U000023E9",  # Fast forward symbol
            width=32,
            height=28,
            corner_radius=14,
            fg_color=("gray70", "gray30"),
            hover_color=("gray60", "gray40"),
            command=lambda: self._handle_seek_relative(10),
        )
        self.forward_button.grid(row=0, column=2, padx=(5, 0))

        # Time label row
        time_frame = ctk.CTkFrame(self.seek_container, fg_color="transparent")
        time_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 5))
        time_frame.grid_columnconfigure(1, weight=1)

        # Current position
        self.position_label = ctk.CTkLabel(
            time_frame,
            text="0:00",
            font=ctk.CTkFont(size=10),
            text_color="gray",
        )
        self.position_label.grid(row=0, column=0, sticky="w")

        # Duration
        self.duration_label = ctk.CTkLabel(
            time_frame,
            text="0:00",
            font=ctk.CTkFont(size=10),
            text_color="gray",
        )
        self.duration_label.grid(row=0, column=2, sticky="e")

        # Initially hide seek controls (will show when media is playing)
        self.seek_container.grid_remove()

    def _format_time(self, seconds: Optional[float]) -> str:
        """Format seconds as MM:SS or H:MM:SS."""
        if seconds is None or seconds < 0:
            return "0:00"
        seconds = int(seconds)
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        if hours > 0:
            return f"{hours}:{minutes:02d}:{secs:02d}"
        return f"{minutes}:{secs:02d}"

    def _handle_seek_drag(self, value: float) -> None:
        """Handle seek slider drag - update position label."""
        if self._updating:
            return

        duration = self.device.state.media_duration
        if duration and duration > 0:
            position = (value / 100) * duration
            self.position_label.configure(text=self._format_time(position))

    def _handle_seek_release(self, event) -> None:
        """Handle seek slider release - send seek to device."""
        if self._updating:
            return

        duration = self.device.state.media_duration
        if duration and duration > 0 and self._on_seek:
            position = (self.seek_slider.get() / 100) * duration
            self._on_seek(self.device, position)

    def _handle_seek_relative(self, offset: float) -> None:
        """Handle skip forward/backward buttons."""
        if self._on_seek_relative:
            self._on_seek_relative(self.device, offset)

    def _get_info_text(self) -> str:
        """Get the info text for the device."""
        parts = []

        # Show if it's a speaker group
        if hasattr(self.device, 'is_group') and self.device.is_group:
            parts.append("\U0001F465 " + _("device_type_group"))  # People icon for group

        # Show room if assigned
        if self.room:
            parts.append(self.room)

        if self.device.ip_address:
            parts.append(self.device.ip_address)

        if self.device.device_type != DeviceType.UNKNOWN:
            type_names = {
                DeviceType.LIGHT: _("device_type_light"),
                DeviceType.SWITCH: _("device_type_switch"),
                DeviceType.PLUG: _("device_type_plug"),
                DeviceType.SENSOR: _("device_type_sensor"),
                DeviceType.THERMOSTAT: _("device_type_thermostat"),
                DeviceType.SPEAKER: _("device_type_speaker"),
                DeviceType.CAMERA: _("device_type_camera"),
            }
            # Don't show speaker type if we already show group
            if not (hasattr(self.device, 'is_group') and self.device.is_group):
                parts.append(type_names.get(self.device.device_type, ""))

        return " • ".join(filter(None, parts))

    def _handle_toggle(self) -> None:
        """Handle power button click."""
        if self._on_toggle:
            self._on_toggle(self.device)

    def _handle_tv_off(self) -> None:
        """Handle TV off button click."""
        if self._on_tv_off:
            self._on_tv_off(self.device)

    def _handle_brightness_change(self, value: float) -> None:
        """Handle brightness slider change."""
        if self._updating:
            return

        level = int(value)
        self.brightness_label.configure(text=f"{level}%")

        if self._on_brightness_change:
            self._on_brightness_change(self.device, level)

    def _handle_settings(self) -> None:
        """Handle settings button click."""
        if self._on_settings:
            self._on_settings(self.device)

    def _update_from_device(self) -> None:
        """Update UI from device state."""
        self._updating = True

        state = self.device.state

        # Update status indicator
        if state.is_online:
            self.status_indicator.configure(text_color="green")
        else:
            self.status_indicator.configure(text_color="gray")

        # Update power button
        if self.power_button:
            if state.is_on:
                self.power_button.configure(
                    fg_color=("green", "#2fa572"),
                    hover_color=("darkgreen", "#1f7a50"),
                )
            else:
                self.power_button.configure(
                    fg_color=("gray70", "gray30"),
                    hover_color=("gray60", "gray40"),
                )

        # Update brightness slider
        if hasattr(self, "brightness_slider"):
            brightness = state.brightness if state.brightness is not None else 0
            self.brightness_slider.set(brightness)
            self.brightness_label.configure(text=f"{brightness}%")

        # Update volume slider
        if hasattr(self, "volume_slider"):
            volume = state.volume if state.volume is not None else 0
            self.volume_slider.set(volume)
            self.volume_label.configure(text=f"{volume}%")

        # Update playback controls
        if hasattr(self, "playback_button"):
            # Update media info
            media_text = ""
            if state.media_title:
                media_text = state.media_title
                if state.media_artist:
                    media_text = f"{state.media_artist} - {state.media_title}"
            self.media_info_label.configure(text=media_text)

            # Update button icon and color based on state
            if state.playback_state == PlaybackState.PLAYING:
                # Show pause icon, green color (active)
                self.playback_button.configure(
                    text="\U000023F8",  # Pause symbol
                    fg_color=("green", "#2fa572"),
                    hover_color=("darkgreen", "#1f7a50"),
                )
            elif state.playback_state == PlaybackState.PAUSED:
                # Show play icon, orange color (paused but has session)
                self.playback_button.configure(
                    text="\U000025B6",  # Play triangle
                    fg_color=("orange", "#e67e22"),
                    hover_color=("darkorange", "#d35400"),
                )
            else:
                # Show play icon, gray color (idle/no session)
                self.playback_button.configure(
                    text="\U000025B6",  # Play triangle
                    fg_color=("gray70", "gray30"),
                    hover_color=("gray60", "gray40"),
                )

        # Update color indicator
        if hasattr(self, "color_indicator") and state.rgb:
            r, g, b = state.rgb
            hex_color = f"#{r:02x}{g:02x}{b:02x}"
            self.color_indicator.configure(text_color=hex_color)

        # Update seek controls
        if hasattr(self, "seek_container"):
            duration = state.media_duration
            position = state.media_position

            # Show/hide seek controls based on whether we have media with duration
            has_media = duration and duration > 0
            if has_media:
                self.seek_container.grid()

                # Update time labels
                self.position_label.configure(text=self._format_time(position))
                self.duration_label.configure(text=self._format_time(duration))

                # Update slider position (as percentage)
                if position is not None:
                    percent = (position / duration) * 100
                    self.seek_slider.set(percent)
                else:
                    self.seek_slider.set(0)
            else:
                self.seek_container.grid_remove()

        self._updating = False

    def refresh(self) -> None:
        """Refresh the card from device state."""
        self._update_from_device()

    def set_device(self, device: BaseDevice, room: Optional[str] = None) -> None:
        """Update the device displayed in this card.

        Args:
            device: The new device to display
            room: Room assignment (optional)
        """
        self.device = device
        if room is not None:
            self.room = room
        self.name_label.configure(text=device.name)
        self.info_label.configure(text=self._get_info_text())

        icon = self.TYPE_ICONS.get(device.device_type, "\U00002753")
        self.icon_label.configure(text=icon)

        self._update_from_device()

    def set_room(self, room: Optional[str]) -> None:
        """Update the room assignment.

        Args:
            room: New room name or None
        """
        self.room = room
        self.info_label.configure(text=self._get_info_text())
