# IoT Device Manager

En Windows-applikation för att hantera lokala IoT-enheter med ett modernt GUI. Inspirerad av Google Home men fokuserad på lokal kontroll utan molntjänster.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)

## Funktioner

- **Automatisk enhetsupptäckt** via mDNS/Zeroconf
- **Stöd för flera enhetstyper:**
  - Google Home / Chromecast-högtalare (volymkontroll, mediainformation)
  - WiZ / Philips smarta lampor (på/av, ljusstyrka, RGB-färg)
  - TP-Link Tapo-lampor (på/av, ljusstyrka, färg)
  - Tuya/Deltaco-lampor (på/av, ljusstyrka, RGB-färg)
- **Modernt GUI** med mörkt/ljust tema (CustomTkinter)
- **System tray-stöd** - minimera till aktivitetsfältet
- **Färgväljare** för RGB-lampor med snabbval och anpassade färger
- **Lokal kontroll** - all kommunikation sker direkt på ditt nätverk

## Nedladdning

### Färdig .exe (enklast)

Ladda ner den senaste versionen direkt:

**[⬇️ Ladda ner IoTDeviceManager.exe](https://github.com/petofr-infoflex/iot-device-manager/releases/latest/download/IoTDeviceManager.exe)**

Dubbelklicka för att köra - ingen installation krävs!

---

## Installation från källkod

### Krav

- Python 3.10 eller senare
- Windows 10/11

### Steg

1. Klona repositoryt:
```bash
git clone https://github.com/petofr-infoflex/iot-device-manager.git
cd iot-device-manager
```

2. Skapa en virtuell miljö (rekommenderas):
```bash
python -m venv venv
venv\Scripts\activate
```

3. Installera beroenden:
```bash
pip install -r requirements.txt
```

4. Kör applikationen:
```bash
python -m iot_manager
```

## Konfiguration

### WiZ-lampor
WiZ-lampor upptäcks automatiskt på nätverket. Inga ytterligare inställningar krävs.

### Chromecast/Google Home
Chromecast-enheter upptäcks automatiskt via mDNS. Se till att din dator och enheterna är på samma nätverk.

### TP-Link Tapo
1. Öppna inställningar (kugghjulet i appen)
2. Gå till fliken "Tapo"
3. Ange dina Tapo-kontouppgifter (e-post och lösenord)
4. Lägg till IP-adresser för dina Tapo-enheter

### Tuya/Deltaco
Tuya-enheter kräver en "Local Key" som hämtas från Tuya IoT Platform:

1. Skapa ett konto på [Tuya IoT Platform](https://iot.tuya.com/)
2. Skapa ett Cloud Project och länka din app (SmartLife/Deltaco Smart Home)
3. Hämta Device ID och Local Key för dina enheter
4. Lägg till enheterna i inställningarna med IP, Device ID och Local Key

## Användning

### Huvudfönster
- Enheter visas som kort med namn, status och kontroller
- Klicka på strömbrytaren för att slå på/av
- Dra i ljusstyrkereglaget för att justera
- Klicka på färgknappen för att öppna färgväljaren (RGB-lampor)

### System Tray
- Klicka på X för att minimera till aktivitetsfältet
- Högerklicka på ikonen för snabbmeny
- Dubbelklicka för att återställa fönstret

### Inställningar
- **Tema:** Välj mellan mörkt, ljust eller systemtema
- **Auto-upptäckt:** Slå på/av automatisk enhetsupptäckt
- **Pollningsintervall:** Hur ofta enhetsstatusen uppdateras

## Projektstruktur

```
src/iot_manager/
├── __init__.py
├── __main__.py          # Entry point
├── app.py               # Huvudapplikation
├── core/
│   └── events.py        # Event-system
├── devices/
│   ├── base.py          # Abstrakt enhetsklass
│   ├── registry.py      # Enhetsregister
│   ├── chromecast.py    # Chromecast-stöd
│   ├── wiz.py           # WiZ-stöd
│   ├── tapo_light.py    # Tapo-stöd
│   └── tuya_light.py    # Tuya-stöd
├── discovery/
│   ├── mdns.py          # mDNS-discovery
│   └── service.py       # Discovery-orkestrator
├── gui/
│   ├── main_window.py   # Huvudfönster
│   ├── settings_dialog.py
│   ├── system_tray.py
│   └── components/
│       ├── device_card.py
│       └── device_list.py
├── storage/
│   └── settings.py      # Inställningshantering
└── utils/
    └── async_helpers.py # Async/threading-brygga
```

## Beroenden

| Paket | Användning |
|-------|-----------|
| customtkinter | Modernt GUI |
| Pillow | Bildhantering |
| pystray | System tray |
| zeroconf | mDNS-discovery |
| pychromecast | Chromecast-kontroll |
| pywizlight | WiZ-kontroll |
| tapo | TP-Link Tapo-kontroll |
| tinytuya | Tuya-kontroll |

## Bygg från källkod

Om du vill bygga .exe-filen själv:

```bash
# Kör build-scriptet (skapar venv, installerar beroenden, bygger exe)
build.bat
```

Exe-filen skapas i `dist/IoTDeviceManager.exe`.

## Bidra

Bidrag är välkomna! Öppna gärna issues eller pull requests.

## Licens

MIT License - se [LICENSE](LICENSE) för detaljer.

## Tack till

- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) för det moderna GUI-ramverket
- [pychromecast](https://github.com/home-assistant-libs/pychromecast) för Chromecast-integration
- [pywizlight](https://github.com/sbidy/pywizlight) för WiZ-lampstöd
- [tinytuya](https://github.com/jasonacox/tinytuya) för Tuya-protokollstöd
