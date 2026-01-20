"""First-run language selector dialog."""

import customtkinter as ctk
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class LanguageSelectorDialog(ctk.CTkToplevel):
    """Dialog for selecting language on first run."""

    def __init__(self, parent=None):
        """Initialize the dialog.

        Args:
            parent: Parent window (optional for first-run)
        """
        super().__init__(parent)

        self.selected_language: Optional[str] = None

        self._setup_window()
        self._setup_ui()

        # Make modal
        if parent:
            self.transient(parent)
        self.grab_set()

        # Center on screen
        self.update_idletasks()
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x = (screen_width - 400) // 2
        y = (screen_height - 300) // 2
        self.geometry(f"+{x}+{y}")

        # Prevent closing without selection
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_window(self) -> None:
        """Configure the dialog window."""
        self.title("Select Language / Välj språk")
        self.geometry("400x300")
        self.resizable(False, False)

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        self.grid_columnconfigure(0, weight=1)

        # Header with both languages
        header = ctk.CTkLabel(
            self,
            text="Select Language\nVälj språk",
            font=ctk.CTkFont(size=20, weight="bold"),
            justify="center",
        )
        header.grid(row=0, column=0, pady=(30, 10), padx=20)

        # Subheader
        subheader = ctk.CTkLabel(
            self,
            text="Please select your preferred language:\nVänligen välj ditt föredragna språk:",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            justify="center",
        )
        subheader.grid(row=1, column=0, pady=(0, 20), padx=20)

        # Language selection frame
        lang_frame = ctk.CTkFrame(self, fg_color="transparent")
        lang_frame.grid(row=2, column=0, pady=10, padx=40, sticky="ew")
        lang_frame.grid_columnconfigure((0, 1), weight=1)

        # English button
        self.english_btn = ctk.CTkButton(
            lang_frame,
            text="English",
            font=ctk.CTkFont(size=16),
            height=60,
            command=lambda: self._select_language("en"),
        )
        self.english_btn.grid(row=0, column=0, padx=10, sticky="ew")

        # Swedish button
        self.swedish_btn = ctk.CTkButton(
            lang_frame,
            text="Svenska",
            font=ctk.CTkFont(size=16),
            height=60,
            command=lambda: self._select_language("sv"),
        )
        self.swedish_btn.grid(row=0, column=1, padx=10, sticky="ew")

        # Note about changing later
        note = ctk.CTkLabel(
            self,
            text="You can change this later in Settings\nDu kan ändra detta senare i Inställningar",
            font=ctk.CTkFont(size=10),
            text_color="gray",
            justify="center",
        )
        note.grid(row=3, column=0, pady=(20, 10), padx=20)

    def _select_language(self, lang: str) -> None:
        """Handle language selection.

        Args:
            lang: Selected language code ("en" or "sv")
        """
        self.selected_language = lang
        logger.info(f"Language selected: {lang}")
        self.destroy()

    def _on_close(self) -> None:
        """Handle window close - default to English if no selection."""
        if self.selected_language is None:
            self.selected_language = "en"
        self.destroy()

    def get_language(self) -> str:
        """Get the selected language.

        Returns:
            Language code ("en" or "sv")
        """
        self.wait_window()
        return self.selected_language or "en"
