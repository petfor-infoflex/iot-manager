"""Scrollable device list component."""

import customtkinter as ctk
from typing import Callable, Optional
import logging

from .device_card import DeviceCard
from ...devices.base import BaseDevice

logger = logging.getLogger(__name__)


class DeviceList(ctk.CTkScrollableFrame):
    """A scrollable list of device cards."""

    def __init__(
        self,
        parent,
        on_toggle: Optional[Callable[[BaseDevice], None]] = None,
        on_brightness_change: Optional[Callable[[BaseDevice, int], None]] = None,
        on_volume_change: Optional[Callable[[BaseDevice, int], None]] = None,
        on_color_change: Optional[Callable[[BaseDevice, tuple[int, int, int]], None]] = None,
        on_play: Optional[Callable[[BaseDevice], None]] = None,
        on_pause: Optional[Callable[[BaseDevice], None]] = None,
        on_settings: Optional[Callable[[BaseDevice], None]] = None,
        on_tv_off: Optional[Callable[[BaseDevice], None]] = None,
        **kwargs,
    ):
        """Initialize the device list.

        Args:
            parent: Parent widget
            on_toggle: Callback when a device power button is clicked
            on_brightness_change: Callback when a device brightness changes
            on_volume_change: Callback when a device volume changes
            on_color_change: Callback when a device color changes
            on_play: Callback when play button is clicked
            on_pause: Callback when pause button is clicked
            on_settings: Callback when device settings is clicked
            on_tv_off: Callback when TV off button is clicked
            **kwargs: Additional arguments for CTkScrollableFrame
        """
        super().__init__(parent, **kwargs)

        self._on_toggle = on_toggle
        self._on_brightness_change = on_brightness_change
        self._on_volume_change = on_volume_change
        self._on_color_change = on_color_change
        self._on_play = on_play
        self._on_pause = on_pause
        self._on_settings = on_settings
        self._on_tv_off = on_tv_off

        self._cards: dict[str, DeviceCard] = {}
        self._devices: dict[str, BaseDevice] = {}
        self._device_rooms: dict[str, Optional[str]] = {}  # device_id -> room

        # Configure grid
        self.grid_columnconfigure(0, weight=1)

        # Empty state label
        self._empty_label = ctk.CTkLabel(
            self,
            text="Inga enheter hittade\n\nSöker efter enheter på nätverket...",
            font=ctk.CTkFont(size=14),
            text_color="gray",
        )
        self._show_empty_state()

    def _show_empty_state(self) -> None:
        """Show the empty state message."""
        self._empty_label.grid(row=0, column=0, pady=50)

    def _hide_empty_state(self) -> None:
        """Hide the empty state message."""
        self._empty_label.grid_forget()

    def add_device(self, device: BaseDevice, room: Optional[str] = None) -> DeviceCard:
        """Add a device to the list.

        Args:
            device: The device to add
            room: Room the device belongs to

        Returns:
            The created DeviceCard
        """
        if device.device_id in self._cards:
            logger.debug(f"Device {device.device_id} already in list, updating")
            return self.update_device(device, room)

        # Hide empty state if showing
        if not self._cards:
            self._hide_empty_state()

        # Create card
        card = DeviceCard(
            self,
            device=device,
            room=room,
            on_toggle=self._on_toggle,
            on_brightness_change=self._on_brightness_change,
            on_volume_change=self._on_volume_change,
            on_color_change=self._on_color_change,
            on_play=self._on_play,
            on_pause=self._on_pause,
            on_settings=self._on_settings,
            on_tv_off=self._on_tv_off,
        )

        # Add to grid
        row = len(self._cards)
        card.grid(row=row, column=0, sticky="ew", pady=5, padx=5)

        self._cards[device.device_id] = card
        self._devices[device.device_id] = device
        self._device_rooms[device.device_id] = room

        logger.debug(f"Added device card for {device.name}")
        return card

    def remove_device(self, device_id: str) -> bool:
        """Remove a device from the list.

        Args:
            device_id: ID of the device to remove

        Returns:
            True if device was removed, False if not found
        """
        if device_id not in self._cards:
            return False

        card = self._cards.pop(device_id)
        self._devices.pop(device_id, None)
        self._device_rooms.pop(device_id, None)

        card.destroy()

        # Reorder remaining cards
        self._reorder_cards()

        # Show empty state if no devices left
        if not self._cards:
            self._show_empty_state()

        logger.debug(f"Removed device card for {device_id}")
        return True

    def update_device(self, device: BaseDevice, room: Optional[str] = None) -> Optional[DeviceCard]:
        """Update a device in the list.

        Args:
            device: The device with updated state
            room: Room assignment (optional, keeps existing if None)

        Returns:
            The updated DeviceCard, or None if not found
        """
        if device.device_id not in self._cards:
            return None

        card = self._cards[device.device_id]
        if room is not None:
            self._device_rooms[device.device_id] = room
        card.set_device(device, self._device_rooms.get(device.device_id))
        self._devices[device.device_id] = device

        return card

    def set_device_room(self, device_id: str, room: Optional[str]) -> bool:
        """Set the room for a device.

        Args:
            device_id: Device ID
            room: Room name or None

        Returns:
            True if device was found and updated
        """
        if device_id not in self._cards:
            return False

        self._device_rooms[device_id] = room
        self._cards[device_id].set_room(room)
        return True

    def get_device_room(self, device_id: str) -> Optional[str]:
        """Get the room for a device.

        Args:
            device_id: Device ID

        Returns:
            Room name or None
        """
        return self._device_rooms.get(device_id)

    def refresh_device(self, device_id: str) -> bool:
        """Refresh a specific device card.

        Args:
            device_id: ID of the device to refresh

        Returns:
            True if device was refreshed, False if not found
        """
        if device_id not in self._cards:
            return False

        self._cards[device_id].refresh()
        return True

    def refresh_all(self) -> None:
        """Refresh all device cards."""
        for card in self._cards.values():
            card.refresh()

    def get_card(self, device_id: str) -> Optional[DeviceCard]:
        """Get a device card by device ID.

        Args:
            device_id: ID of the device

        Returns:
            The DeviceCard, or None if not found
        """
        return self._cards.get(device_id)

    def get_device(self, device_id: str) -> Optional[BaseDevice]:
        """Get a device by ID.

        Args:
            device_id: ID of the device

        Returns:
            The device, or None if not found
        """
        return self._devices.get(device_id)

    def _reorder_cards(self) -> None:
        """Reorder cards after removal."""
        for i, card in enumerate(self._cards.values()):
            card.grid(row=i, column=0, sticky="ew", pady=5, padx=5)

    def clear(self) -> None:
        """Remove all devices from the list."""
        for card in list(self._cards.values()):
            card.destroy()

        self._cards.clear()
        self._devices.clear()
        self._device_rooms.clear()
        self._show_empty_state()

    @property
    def device_count(self) -> int:
        """Get the number of devices in the list."""
        return len(self._cards)

    @property
    def devices(self) -> list[BaseDevice]:
        """Get all devices in the list."""
        return list(self._devices.values())

    def __len__(self) -> int:
        return len(self._cards)

    def __contains__(self, device_id: str) -> bool:
        return device_id in self._cards
