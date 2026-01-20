"""Device settings dialog for renaming and assigning rooms."""

import customtkinter as ctk
from typing import TYPE_CHECKING, Optional, Callable
import logging

from ...i18n import _

if TYPE_CHECKING:
    from ...devices.base import BaseDevice

logger = logging.getLogger(__name__)


class DeviceSettingsDialog(ctk.CTkToplevel):
    """Dialog for editing device settings."""

    def __init__(
        self,
        parent,
        device: "BaseDevice",
        rooms: list[str],
        current_room: Optional[str] = None,
        on_save: Optional[Callable[[str, Optional[str]], None]] = None,
        on_delete: Optional[Callable[[], None]] = None,
    ):
        """Initialize the dialog.

        Args:
            parent: Parent window
            device: The device to configure
            rooms: List of available rooms
            current_room: Current room assignment
            on_save: Callback with (new_name, room) when saved
            on_delete: Callback when device is deleted
        """
        super().__init__(parent)

        self.device = device
        self.rooms = rooms
        self.current_room = current_room
        self._on_save = on_save
        self._on_delete = on_delete

        self._setup_window()
        self._setup_ui()

        # Make modal
        self.transient(parent)
        self.grab_set()

    def _setup_window(self) -> None:
        """Configure the dialog window."""
        self.title(f"{_('settings')} - {self.device.name}")
        self.geometry("400x350")
        self.resizable(False, False)

        # Center on parent
        self.update_idletasks()
        parent = self.master
        x = parent.winfo_x() + (parent.winfo_width() - 400) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 350) // 2
        self.geometry(f"+{x}+{y}")

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.grid_columnconfigure(0, weight=1)

        # Header
        header = ctk.CTkLabel(
            self,
            text=_("device_settings"),
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        header.grid(row=0, column=0, pady=(20, 10), padx=20)

        # Device info
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=5)

        info_text = f"ID: {self.device.device_id[:20]}..."
        if self.device.ip_address:
            info_text += f"\nIP: {self.device.ip_address}"

        info_label = ctk.CTkLabel(
            info_frame,
            text=info_text,
            font=ctk.CTkFont(size=11),
            text_color="gray",
            justify="left",
        )
        info_label.pack(anchor="w")

        # Name field
        name_frame = ctk.CTkFrame(self, fg_color="transparent")
        name_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(15, 5))

        name_label = ctk.CTkLabel(
            name_frame,
            text=_("name"),
            font=ctk.CTkFont(size=13),
        )
        name_label.pack(anchor="w")

        self.name_entry = ctk.CTkEntry(
            name_frame,
            width=360,
            height=35,
        )
        self.name_entry.pack(fill="x", pady=(5, 0))
        self.name_entry.insert(0, self.device.name)

        # Room selection
        room_frame = ctk.CTkFrame(self, fg_color="transparent")
        room_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=(15, 5))

        room_label = ctk.CTkLabel(
            room_frame,
            text=_("room"),
            font=ctk.CTkFont(size=13),
        )
        room_label.pack(anchor="w")

        # Room dropdown with option to add new
        self._no_room_text = _("no_room")
        self._add_room_text = _("add_new_room")
        room_options = [self._no_room_text] + self.rooms + [self._add_room_text]

        current_value = self.current_room if self.current_room else self._no_room_text

        self.room_var = ctk.StringVar(value=current_value)
        self.room_dropdown = ctk.CTkComboBox(
            room_frame,
            width=360,
            height=35,
            values=room_options,
            variable=self.room_var,
            command=self._on_room_selected,
        )
        self.room_dropdown.pack(fill="x", pady=(5, 0))

        # New room entry (hidden by default)
        self.new_room_frame = ctk.CTkFrame(room_frame, fg_color="transparent")

        self.new_room_entry = ctk.CTkEntry(
            self.new_room_frame,
            width=360,
            height=35,
            placeholder_text=_("enter_new_room_name"),
        )
        self.new_room_entry.pack(fill="x", pady=(5, 0))

        # Buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.grid(row=5, column=0, sticky="ew", padx=20, pady=(30, 20))
        button_frame.grid_columnconfigure((0, 1, 2), weight=1)

        # Delete button
        delete_btn = ctk.CTkButton(
            button_frame,
            text=_("delete"),
            width=100,
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            text_color=("#cc0000", "#ff4444"),
            command=self._handle_delete,
        )
        delete_btn.grid(row=0, column=0, sticky="w")

        # Cancel button
        cancel_btn = ctk.CTkButton(
            button_frame,
            text=_("cancel"),
            width=100,
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            command=self.destroy,
        )
        cancel_btn.grid(row=0, column=1)

        # Save button
        save_btn = ctk.CTkButton(
            button_frame,
            text=_("save"),
            width=100,
            command=self._handle_save,
        )
        save_btn.grid(row=0, column=2, sticky="e")

    def _on_room_selected(self, value: str) -> None:
        """Handle room selection change."""
        if value == self._add_room_text:
            self.new_room_frame.pack(fill="x", pady=(5, 0))
            self.new_room_entry.focus()
        else:
            self.new_room_frame.pack_forget()

    def _handle_save(self) -> None:
        """Handle save button click."""
        new_name = self.name_entry.get().strip()

        if not new_name:
            # Show error - name is required
            self.name_entry.configure(border_color="red")
            return

        # Get room
        room = self.room_var.get()

        if room == self._add_room_text:
            room = self.new_room_entry.get().strip()
            if not room:
                self.new_room_entry.configure(border_color="red")
                return
        elif room == self._no_room_text:
            room = None

        logger.info(f"Saving device settings: name={new_name}, room={room}")

        if self._on_save:
            self._on_save(new_name, room)

        self.destroy()

    def _handle_delete(self) -> None:
        """Handle delete button click."""
        # Confirm deletion
        confirm = ConfirmDialog(
            self,
            title=_("delete_device"),
            message=_("delete_device_confirm", name=self.device.name),
        )

        if confirm.result:
            logger.info(f"Deleting device: {self.device.device_id}")
            if self._on_delete:
                self._on_delete()
            self.destroy()


class ConfirmDialog(ctk.CTkToplevel):
    """Simple confirmation dialog."""

    def __init__(self, parent, title: str, message: str):
        super().__init__(parent)

        self.result = False

        self.title(title)
        self.geometry("300x150")
        self.resizable(False, False)

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 300) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 150) // 2
        self.geometry(f"+{x}+{y}")

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Message
        msg_label = ctk.CTkLabel(
            self,
            text=message,
            font=ctk.CTkFont(size=13),
            wraplength=260,
        )
        msg_label.pack(pady=(30, 20))

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=10)

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text=_("cancel"),
            width=80,
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            command=self._cancel,
        )
        cancel_btn.pack(side="left", padx=10)

        confirm_btn = ctk.CTkButton(
            btn_frame,
            text=_("delete"),
            width=80,
            fg_color=("#cc0000", "#aa0000"),
            hover_color=("#990000", "#880000"),
            command=self._confirm,
        )
        confirm_btn.pack(side="left", padx=10)

        # Wait for dialog to close
        self.wait_window()

    def _cancel(self) -> None:
        self.result = False
        self.destroy()

    def _confirm(self) -> None:
        self.result = True
        self.destroy()
