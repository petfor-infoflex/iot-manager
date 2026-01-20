"""Room manager dialog for organizing devices into rooms."""

import customtkinter as ctk
from typing import Callable, Optional
import logging

from ...i18n import _

logger = logging.getLogger(__name__)


class RoomManagerDialog(ctk.CTkToplevel):
    """Dialog for managing rooms."""

    def __init__(
        self,
        parent,
        rooms: list[str],
        on_rooms_changed: Optional[Callable[[list[str]], None]] = None,
    ):
        """Initialize the dialog.

        Args:
            parent: Parent window
            rooms: Current list of rooms
            on_rooms_changed: Callback when rooms are modified
        """
        super().__init__(parent)

        self.rooms = list(rooms)
        self._on_rooms_changed = on_rooms_changed

        self._setup_window()
        self._setup_ui()

        # Make modal
        self.transient(parent)
        self.grab_set()

    def _setup_window(self) -> None:
        """Configure the dialog window."""
        self.title(_("manage_rooms"))
        self.geometry("350x450")
        self.resizable(False, False)

        # Center on parent
        self.update_idletasks()
        parent = self.master
        x = parent.winfo_x() + (parent.winfo_width() - 350) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 450) // 2
        self.geometry(f"+{x}+{y}")

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        header = ctk.CTkLabel(
            self,
            text=_("manage_rooms"),
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        header.grid(row=0, column=0, pady=(20, 10), padx=20)

        # Room list
        self.room_list_frame = ctk.CTkScrollableFrame(self)
        self.room_list_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        self.room_list_frame.grid_columnconfigure(0, weight=1)

        self._refresh_room_list()

        # Add room section
        add_frame = ctk.CTkFrame(self, fg_color="transparent")
        add_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=10)
        add_frame.grid_columnconfigure(0, weight=1)

        self.new_room_entry = ctk.CTkEntry(
            add_frame,
            placeholder_text=_("new_room_name"),
            height=35,
        )
        self.new_room_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))

        add_btn = ctk.CTkButton(
            add_frame,
            text="+",
            width=40,
            height=35,
            command=self._add_room,
        )
        add_btn.grid(row=0, column=1)

        # Bind Enter key to add room
        self.new_room_entry.bind("<Return>", lambda e: self._add_room())

        # Close button
        close_btn = ctk.CTkButton(
            self,
            text=_("close"),
            width=100,
            command=self.destroy,
        )
        close_btn.grid(row=3, column=0, pady=(10, 20))

    def _refresh_room_list(self) -> None:
        """Refresh the room list display."""
        # Clear existing items
        for widget in self.room_list_frame.winfo_children():
            widget.destroy()

        if not self.rooms:
            empty_label = ctk.CTkLabel(
                self.room_list_frame,
                text=_("no_rooms_created"),
                text_color="gray",
            )
            empty_label.pack(pady=20)
            return

        # Add room items
        for i, room in enumerate(self.rooms):
            self._create_room_item(room, i)

    def _create_room_item(self, room: str, index: int) -> None:
        """Create a room list item.

        Args:
            room: Room name
            index: Index in list
        """
        item_frame = ctk.CTkFrame(self.room_list_frame)
        item_frame.grid(row=index, column=0, sticky="ew", pady=2)
        item_frame.grid_columnconfigure(0, weight=1)

        # Room name
        name_label = ctk.CTkLabel(
            item_frame,
            text=room,
            font=ctk.CTkFont(size=13),
            anchor="w",
        )
        name_label.grid(row=0, column=0, sticky="w", padx=10, pady=8)

        # Edit button
        edit_btn = ctk.CTkButton(
            item_frame,
            text="\U0000270E",  # Pencil
            width=30,
            height=30,
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            command=lambda r=room: self._edit_room(r),
        )
        edit_btn.grid(row=0, column=1, padx=2)

        # Delete button
        delete_btn = ctk.CTkButton(
            item_frame,
            text="\U0001F5D1",  # Trash
            width=30,
            height=30,
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            text_color=("#cc0000", "#ff4444"),
            command=lambda r=room: self._delete_room(r),
        )
        delete_btn.grid(row=0, column=2, padx=(2, 5))

    def _add_room(self) -> None:
        """Add a new room."""
        name = self.new_room_entry.get().strip()

        if not name:
            return

        if name in self.rooms:
            # Room already exists
            self.new_room_entry.configure(border_color="red")
            return

        self.rooms.append(name)
        self.rooms.sort()
        self._refresh_room_list()
        self._notify_change()

        # Clear entry
        self.new_room_entry.delete(0, "end")
        self.new_room_entry.configure(border_color=None)

        logger.info(f"Added room: {name}")

    def _edit_room(self, old_name: str) -> None:
        """Edit a room name.

        Args:
            old_name: Current room name
        """
        dialog = EditRoomDialog(self, old_name)

        if dialog.result and dialog.result != old_name:
            # Update room name
            index = self.rooms.index(old_name)
            self.rooms[index] = dialog.result
            self.rooms.sort()
            self._refresh_room_list()
            self._notify_change()

            logger.info(f"Renamed room: {old_name} -> {dialog.result}")

    def _delete_room(self, room: str) -> None:
        """Delete a room.

        Args:
            room: Room to delete
        """
        if room in self.rooms:
            self.rooms.remove(room)
            self._refresh_room_list()
            self._notify_change()

            logger.info(f"Deleted room: {room}")

    def _notify_change(self) -> None:
        """Notify that rooms have changed."""
        if self._on_rooms_changed:
            self._on_rooms_changed(self.rooms)


class EditRoomDialog(ctk.CTkToplevel):
    """Dialog for editing a room name."""

    def __init__(self, parent, current_name: str):
        super().__init__(parent)

        self.result: Optional[str] = None

        self.title(_("edit_room"))
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

        # Name entry
        label = ctk.CTkLabel(
            self,
            text=_("room_name"),
            font=ctk.CTkFont(size=13),
        )
        label.pack(pady=(30, 5))

        self.entry = ctk.CTkEntry(self, width=200, height=35)
        self.entry.pack(pady=5)
        self.entry.insert(0, current_name)
        self.entry.select_range(0, "end")
        self.entry.focus()

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text=_("cancel"),
            width=80,
            fg_color="transparent",
            hover_color=("gray80", "gray30"),
            command=self._cancel,
        )
        cancel_btn.pack(side="left", padx=10)

        save_btn = ctk.CTkButton(
            btn_frame,
            text=_("save"),
            width=80,
            command=self._save,
        )
        save_btn.pack(side="left", padx=10)

        # Bind Enter key
        self.entry.bind("<Return>", lambda e: self._save())

        # Wait for dialog to close
        self.wait_window()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()

    def _save(self) -> None:
        name = self.entry.get().strip()
        if name:
            self.result = name
        self.destroy()
