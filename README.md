# IoT Device Manager

A Windows application for managing local IoT devices with a modern GUI. Inspired by Google Home but focused on local control without cloud services.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Features

- **Automatic device discovery** via mDNS/Zeroconf
- **Support for multiple device types:**
  - Google Home / Chromecast speakers (volume control, media information)
  - WiZ / Philips smart lights (on/off, brightness, RGB color)
  - TP-Link Tapo lights (on/off, brightness, color)
  - Tuya/Deltaco lights (on/off, brightness, RGB color)
- **Modern GUI** with dark/light theme (CustomTkinter)
- **System tray support** - minimize to taskbar
- **Color picker** for RGB lights with quick presets and custom colors
- **Local control** - all communication happens directly on your network
- **Multi-language support** (English and Swedish)

## Download

### Ready-to-use .exe (easiest)

Download the latest version directly:

**[Download IoTDeviceManager.exe](https://github.com/petfor-infoflex/iot-manager/releases/latest/download/IoTDeviceManager.exe)**

Double-click to run - no installation required!

---

## Installation from source

### Requirements

- Python 3.10 or later
- Windows 10/11

### Steps

1. Clone the repository:
```bash
git clone https://github.com/petfor-infoflex/iot-manager.git
cd iot-manager
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python -m iot_manager
```

## Configuration

### WiZ lights
WiZ lights are automatically discovered on the network. No additional settings required.

### Chromecast/Google Home
Chromecast devices are automatically discovered via mDNS. Make sure your computer and devices are on the same network.

### TP-Link Tapo
1. Open settings (gear icon in the app)
2. Go to the "Tapo" tab
3. Enter your Tapo account credentials (email and password)
4. Add IP addresses for your Tapo devices

### Tuya/Deltaco
Tuya devices require a "Local Key" obtained from Tuya IoT Platform:

1. Create an account at [Tuya IoT Platform](https://iot.tuya.com/)
2. Create a Cloud Project and link your app (SmartLife/Deltaco Smart Home)
3. Get the Device ID and Local Key for your devices
4. Add devices in settings with IP, Device ID, and Local Key

## Usage

### Main window
- Devices are displayed as cards with name, status, and controls
- Click the power button to turn on/off
- Drag the brightness slider to adjust
- Click the color button to open the color picker (RGB lights)

### System Tray
- Click X to minimize to taskbar
- Right-click on icon for quick menu
- Double-click to restore window

### Settings
- **Theme:** Choose between dark, light, or system theme
- **Auto-discovery:** Enable/disable automatic device discovery
- **Polling interval:** How often device status is updated
- **Language:** Select English or Swedish (requires restart)

## Project Structure

```
src/iot_manager/
├── __init__.py
├── __main__.py          # Entry point
├── app.py               # Main application
├── core/
│   └── events.py        # Event system
├── devices/
│   ├── base.py          # Abstract device class
│   ├── registry.py      # Device registry
│   ├── chromecast.py    # Chromecast support
│   ├── wiz.py           # WiZ support
│   ├── tapo_light.py    # Tapo support
│   └── tuya_light.py    # Tuya support
├── discovery/
│   ├── mdns.py          # mDNS discovery
│   └── service.py       # Discovery orchestrator
├── gui/
│   ├── main_window.py   # Main window
│   ├── settings_dialog.py
│   ├── system_tray.py
│   └── components/
│       ├── device_card.py
│       └── device_list.py
├── i18n/
│   ├── __init__.py      # Translation system
│   ├── en.json          # English translations
│   └── sv.json          # Swedish translations
├── storage/
│   └── settings.py      # Settings management
└── utils/
    └── async_helpers.py # Async/threading bridge
```

## Dependencies

| Package | Usage |
|---------|-------|
| customtkinter | Modern GUI |
| Pillow | Image handling |
| pystray | System tray |
| zeroconf | mDNS discovery |
| pychromecast | Chromecast control |
| pywizlight | WiZ control |
| tapo | TP-Link Tapo control |
| tinytuya | Tuya control |

## Contributing

Contributions are welcome! Feel free to open issues or pull requests.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Credits

- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) for the modern GUI framework
- [pychromecast](https://github.com/home-assistant-libs/pychromecast) for Chromecast integration
- [pywizlight](https://github.com/sbidy/pywizlight) for WiZ light support
- [tinytuya](https://github.com/jasonacox/tinytuya) for Tuya protocol support
