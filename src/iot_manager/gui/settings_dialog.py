"""Settings dialog for configuring the application."""

import customtkinter as ctk
from typing import Optional, Callable
import logging
import threading

logger = logging.getLogger(__name__)

# Check if tinytuya is available
try:
    import tinytuya
    TINYTUYA_AVAILABLE = True
except ImportError:
    TINYTUYA_AVAILABLE = False


class SettingsDialog(ctk.CTkToplevel):
    """Settings dialog window."""

    def __init__(
        self,
        parent,
        settings_manager,
        on_save: Optional[Callable] = None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)

        self.settings_manager = settings_manager
        self._on_save = on_save
        self._scanned_tuya_devices: list[dict] = []

        self.title("Inställningar")
        self.geometry("700x600")
        self.resizable(True, True)

        # Make modal
        self.transient(parent)
        self.grab_set()

        # Load current settings
        self._settings = settings_manager.load()

        self._setup_ui()

        # Center on parent
        self.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_y() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _setup_ui(self) -> None:
        """Set up the dialog UI."""
        # Create tabview for different settings categories
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        # Add tabs
        self.tabview.add("Allmänt")
        self.tabview.add("Tapo")
        self.tabview.add("Tuya/Deltaco")

        self._setup_general_tab()
        self._setup_tapo_tab()
        self._setup_tuya_tab()

        # Bottom buttons
        button_frame = ctk.CTkFrame(self, fg_color="transparent")
        button_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(
            button_frame,
            text="Avbryt",
            width=100,
            fg_color=("gray70", "gray30"),
            command=self.destroy,
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            button_frame,
            text="Spara",
            width=100,
            command=self._save_settings,
        ).pack(side="right", padx=5)

    def _setup_general_tab(self) -> None:
        """Set up the general settings tab."""
        tab = self.tabview.tab("Allmänt")

        # Theme selection
        theme_frame = ctk.CTkFrame(tab)
        theme_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            theme_frame,
            text="Tema",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.theme_var = ctk.StringVar(value=self._settings.theme)
        theme_options = ctk.CTkFrame(theme_frame, fg_color="transparent")
        theme_options.pack(fill="x", padx=10, pady=5)

        for value, label in [("dark", "Mörkt"), ("light", "Ljust"), ("system", "System")]:
            ctk.CTkRadioButton(
                theme_options,
                text=label,
                variable=self.theme_var,
                value=value,
            ).pack(side="left", padx=10)

        # Auto discover
        discover_frame = ctk.CTkFrame(tab)
        discover_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            discover_frame,
            text="Upptäckt",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.auto_discover_var = ctk.BooleanVar(value=self._settings.auto_discover)
        ctk.CTkCheckBox(
            discover_frame,
            text="Upptäck enheter automatiskt vid start",
            variable=self.auto_discover_var,
        ).pack(anchor="w", padx=10, pady=5)

        # Start minimized
        self.start_minimized_var = ctk.BooleanVar(value=self._settings.start_minimized)
        ctk.CTkCheckBox(
            discover_frame,
            text="Starta minimerad i systemfältet",
            variable=self.start_minimized_var,
        ).pack(anchor="w", padx=10, pady=5)

    def _setup_tapo_tab(self) -> None:
        """Set up the Tapo settings tab."""
        tab = self.tabview.tab("Tapo")

        # Info label
        info_frame = ctk.CTkFrame(tab)
        info_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            info_frame,
            text="TP-Link Tapo-lampor kräver dina molnuppgifter för att styras lokalt.",
            font=ctk.CTkFont(size=12),
            wraplength=500,
        ).pack(padx=10, pady=10)

        # Credentials
        cred_frame = ctk.CTkFrame(tab)
        cred_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            cred_frame,
            text="Tapo-konto",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        # Username
        user_frame = ctk.CTkFrame(cred_frame, fg_color="transparent")
        user_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(user_frame, text="E-post:", width=80).pack(side="left")
        self.tapo_username_entry = ctk.CTkEntry(user_frame, width=300)
        self.tapo_username_entry.pack(side="left", padx=5)
        self.tapo_username_entry.insert(0, self._settings.tapo_username)

        # Password
        pass_frame = ctk.CTkFrame(cred_frame, fg_color="transparent")
        pass_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(pass_frame, text="Lösenord:", width=80).pack(side="left")
        self.tapo_password_entry = ctk.CTkEntry(pass_frame, width=300, show="*")
        self.tapo_password_entry.pack(side="left", padx=5)
        self.tapo_password_entry.insert(0, self._settings.tapo_password)

        # Device IPs
        ip_frame = ctk.CTkFrame(tab)
        ip_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            ip_frame,
            text="Tapo-enhets IP-adresser (en per rad)",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=10, pady=(10, 5))

        self.tapo_ips_text = ctk.CTkTextbox(ip_frame, height=100)
        self.tapo_ips_text.pack(fill="x", padx=10, pady=5)
        if self._settings.tapo_device_ips:
            self.tapo_ips_text.insert("1.0", "\n".join(self._settings.tapo_device_ips))

    def _setup_tuya_tab(self) -> None:
        """Set up the Tuya/Deltaco settings tab."""
        tab = self.tabview.tab("Tuya/Deltaco")

        # Info label
        info_frame = ctk.CTkFrame(tab)
        info_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            info_frame,
            text="Tuya/Deltaco-enheter kräver Device ID och Local Key.\n"
                 "Skanna nätverket för att hitta enheter, sedan måste du\n"
                 "hämta Local Key från Tuya IoT Platform.",
            font=ctk.CTkFont(size=12),
            wraplength=500,
            justify="left",
        ).pack(padx=10, pady=10)

        # Scan button
        scan_frame = ctk.CTkFrame(tab)
        scan_frame.pack(fill="x", padx=10, pady=10)

        self.scan_button = ctk.CTkButton(
            scan_frame,
            text="Skanna nätverk efter Tuya-enheter",
            command=self._scan_tuya_devices,
        )
        self.scan_button.pack(side="left", padx=10, pady=10)

        self.scan_status = ctk.CTkLabel(scan_frame, text="")
        self.scan_status.pack(side="left", padx=10)

        # Scanned devices list
        self.scanned_frame = ctk.CTkFrame(tab)
        self.scanned_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            self.scanned_frame,
            text="Hittade enheter (klicka för att lägga till):",
            font=ctk.CTkFont(size=12, weight="bold"),
        ).pack(anchor="w", padx=10, pady=5)

        self.scanned_list = ctk.CTkScrollableFrame(self.scanned_frame, height=100)
        self.scanned_list.pack(fill="x", padx=10, pady=5)

        # Configured devices
        config_frame = ctk.CTkFrame(tab)
        config_frame.pack(fill="both", expand=True, padx=10, pady=10)

        header_frame = ctk.CTkFrame(config_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            header_frame,
            text="Konfigurerade Tuya-enheter",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(side="left")

        ctk.CTkButton(
            header_frame,
            text="+ Lägg till manuellt",
            width=140,
            command=self._add_tuya_device_dialog,
        ).pack(side="right")

        # Device list
        self.tuya_devices_frame = ctk.CTkScrollableFrame(config_frame, height=150)
        self.tuya_devices_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # Populate existing devices
        self._refresh_tuya_device_list()

    def _scan_tuya_devices(self) -> None:
        """Scan for Tuya devices on the network."""
        if not TINYTUYA_AVAILABLE:
            self.scan_status.configure(text="tinytuya ej installerat!")
            return

        self.scan_button.configure(state="disabled")
        self.scan_status.configure(text="Skannar...")

        def do_scan():
            try:
                # Scan for devices (this takes a few seconds)
                devices = tinytuya.deviceScan(verbose=False)
                self._scanned_tuya_devices = list(devices.values()) if devices else []
                # Update UI on main thread
                self.after(0, self._update_scanned_list)
            except Exception as e:
                logger.error(f"Error scanning for Tuya devices: {e}")
                self.after(0, lambda: self.scan_status.configure(text=f"Fel: {e}"))
            finally:
                self.after(0, lambda: self.scan_button.configure(state="normal"))

        thread = threading.Thread(target=do_scan, daemon=True)
        thread.start()

    def _update_scanned_list(self) -> None:
        """Update the list of scanned devices."""
        # Clear existing
        for widget in self.scanned_list.winfo_children():
            widget.destroy()

        if not self._scanned_tuya_devices:
            self.scan_status.configure(text="Inga enheter hittades")
            ctk.CTkLabel(
                self.scanned_list,
                text="Inga Tuya-enheter hittades på nätverket",
                text_color="gray",
            ).pack(pady=10)
            return

        self.scan_status.configure(text=f"Hittade {len(self._scanned_tuya_devices)} enheter")

        for device in self._scanned_tuya_devices:
            device_frame = ctk.CTkFrame(self.scanned_list)
            device_frame.pack(fill="x", pady=2)

            ip = device.get("ip", "?")
            dev_id = device.get("gwId", device.get("id", "?"))
            version = device.get("version", "3.3")

            ctk.CTkLabel(
                device_frame,
                text=f"IP: {ip}  |  ID: {dev_id[:20]}...  |  v{version}",
                font=ctk.CTkFont(size=11),
            ).pack(side="left", padx=10, pady=5)

            ctk.CTkButton(
                device_frame,
                text="Lägg till",
                width=80,
                height=28,
                command=lambda d=device: self._add_scanned_device(d),
            ).pack(side="right", padx=5, pady=5)

    def _add_scanned_device(self, device: dict) -> None:
        """Add a scanned device - opens dialog to enter local key."""
        ip = device.get("ip", "")
        dev_id = device.get("gwId", device.get("id", ""))
        version = device.get("version", "3.3")

        self._show_tuya_device_dialog(
            name="",
            ip=ip,
            device_id=dev_id,
            local_key="",
            version=str(version),
        )

    def _add_tuya_device_dialog(self) -> None:
        """Show dialog to add a Tuya device manually."""
        self._show_tuya_device_dialog()

    def _show_tuya_device_dialog(
        self,
        name: str = "",
        ip: str = "",
        device_id: str = "",
        local_key: str = "",
        version: str = "3.3",
        edit_index: Optional[int] = None,
    ) -> None:
        """Show dialog to add/edit a Tuya device."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Lägg till Tuya-enhet" if edit_index is None else "Redigera Tuya-enhet")
        dialog.geometry("450x350")
        dialog.transient(self)
        dialog.grab_set()

        # Center on parent
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_y() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        # Form
        form_frame = ctk.CTkFrame(dialog)
        form_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Name
        ctk.CTkLabel(form_frame, text="Namn:").grid(row=0, column=0, sticky="w", pady=5)
        name_entry = ctk.CTkEntry(form_frame, width=300)
        name_entry.grid(row=0, column=1, pady=5, padx=10)
        name_entry.insert(0, name)

        # IP
        ctk.CTkLabel(form_frame, text="IP-adress:").grid(row=1, column=0, sticky="w", pady=5)
        ip_entry = ctk.CTkEntry(form_frame, width=300)
        ip_entry.grid(row=1, column=1, pady=5, padx=10)
        ip_entry.insert(0, ip)

        # Device ID
        ctk.CTkLabel(form_frame, text="Device ID:").grid(row=2, column=0, sticky="w", pady=5)
        id_entry = ctk.CTkEntry(form_frame, width=300)
        id_entry.grid(row=2, column=1, pady=5, padx=10)
        id_entry.insert(0, device_id)

        # Local Key
        ctk.CTkLabel(form_frame, text="Local Key:").grid(row=3, column=0, sticky="w", pady=5)
        key_entry = ctk.CTkEntry(form_frame, width=300)
        key_entry.grid(row=3, column=1, pady=5, padx=10)
        key_entry.insert(0, local_key)

        # Version
        ctk.CTkLabel(form_frame, text="Version:").grid(row=4, column=0, sticky="w", pady=5)
        version_entry = ctk.CTkEntry(form_frame, width=300)
        version_entry.grid(row=4, column=1, pady=5, padx=10)
        version_entry.insert(0, version)

        # Help text
        ctk.CTkLabel(
            form_frame,
            text="Local Key hämtas från Tuya IoT Platform.\nKör 'python -m tinytuya wizard' för hjälp.",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        ).grid(row=5, column=0, columnspan=2, pady=10)

        # Buttons
        btn_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)

        def save_device():
            device_config = {
                "name": name_entry.get() or f"Tuya {ip_entry.get()}",
                "ip": ip_entry.get(),
                "id": id_entry.get(),
                "key": key_entry.get(),
                "version": float(version_entry.get() or "3.3"),
            }

            if not device_config["ip"] or not device_config["id"] or not device_config["key"]:
                # Show error
                return

            # Update or add to list
            tuya_devices = list(self._settings.tuya_devices)
            if edit_index is not None:
                tuya_devices[edit_index] = device_config
            else:
                tuya_devices.append(device_config)

            self._settings.tuya_devices = tuya_devices
            self._refresh_tuya_device_list()
            dialog.destroy()

        ctk.CTkButton(
            btn_frame,
            text="Avbryt",
            width=100,
            fg_color=("gray70", "gray30"),
            command=dialog.destroy,
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="Spara",
            width=100,
            command=save_device,
        ).pack(side="right", padx=5)

    def _refresh_tuya_device_list(self) -> None:
        """Refresh the list of configured Tuya devices."""
        # Clear existing
        for widget in self.tuya_devices_frame.winfo_children():
            widget.destroy()

        if not self._settings.tuya_devices:
            ctk.CTkLabel(
                self.tuya_devices_frame,
                text="Inga Tuya-enheter konfigurerade",
                text_color="gray",
            ).pack(pady=20)
            return

        for i, device in enumerate(self._settings.tuya_devices):
            device_frame = ctk.CTkFrame(self.tuya_devices_frame)
            device_frame.pack(fill="x", pady=2)

            name = device.get("name", "Okänd")
            ip = device.get("ip", "?")
            has_key = "Ja" if device.get("key") else "Nej"

            ctk.CTkLabel(
                device_frame,
                text=f"{name}  |  {ip}  |  Key: {has_key}",
                font=ctk.CTkFont(size=12),
            ).pack(side="left", padx=10, pady=8)

            # Delete button
            ctk.CTkButton(
                device_frame,
                text="Ta bort",
                width=70,
                height=28,
                fg_color=("gray70", "gray30"),
                hover_color=("red", "#c0392b"),
                command=lambda idx=i: self._delete_tuya_device(idx),
            ).pack(side="right", padx=5, pady=5)

            # Edit button
            ctk.CTkButton(
                device_frame,
                text="Redigera",
                width=70,
                height=28,
                command=lambda idx=i, d=device: self._show_tuya_device_dialog(
                    name=d.get("name", ""),
                    ip=d.get("ip", ""),
                    device_id=d.get("id", ""),
                    local_key=d.get("key", ""),
                    version=str(d.get("version", "3.3")),
                    edit_index=idx,
                ),
            ).pack(side="right", padx=5, pady=5)

    def _delete_tuya_device(self, index: int) -> None:
        """Delete a Tuya device from the list."""
        tuya_devices = list(self._settings.tuya_devices)
        if 0 <= index < len(tuya_devices):
            tuya_devices.pop(index)
            self._settings.tuya_devices = tuya_devices
            self._refresh_tuya_device_list()

    def _save_settings(self) -> None:
        """Save all settings and close dialog."""
        # General settings
        self._settings.theme = self.theme_var.get()
        self._settings.auto_discover = self.auto_discover_var.get()
        self._settings.start_minimized = self.start_minimized_var.get()

        # Tapo settings
        self._settings.tapo_username = self.tapo_username_entry.get()
        self._settings.tapo_password = self.tapo_password_entry.get()

        # Parse Tapo IPs
        ips_text = self.tapo_ips_text.get("1.0", "end").strip()
        if ips_text:
            self._settings.tapo_device_ips = [
                ip.strip() for ip in ips_text.split("\n") if ip.strip()
            ]
        else:
            self._settings.tapo_device_ips = []

        # Tuya devices are already updated in _settings

        # Save to disk
        self.settings_manager.save(self._settings)

        # Apply theme immediately
        ctk.set_appearance_mode(self._settings.theme)

        # Callback
        if self._on_save:
            self._on_save(self._settings)

        self.destroy()
