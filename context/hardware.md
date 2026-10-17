# Hardware Context: Parts, Wiring & Configuration

## 1. Parts List

- **Single-Board Computer (SBC):** Raspberry Pi 4 Model B (2GB, 4GB, or 8GB)
- **Display & Touch Panel:** Kuman 3.5" HDMI Display-B 480×320 Dots V1.0 (Model MPI3508)
  - Interface: Full HDMI for high-speed 60 FPS video
  - Touch Controller: Onboard Texas Instruments / XPT2046 resistive touch controller
- **Display Adapters:** 
  - Micro-HDMI (Male) to Standard HDMI (Female) adapter / bridge (connects Raspberry Pi 4 Micro-HDMI Port 0 to the Kuman display HDMI input)
- **Microphone / Audio Input:** USB Plug-and-Play Microphone (or USB Audio DAC / I2S MEMS mic)
- **Power Supply:** 5V / 3A USB-C Power Adapter (or portable 5V/3A USB-C Li-Ion power bank)
- **Storage:** MicroSD Card (Class 10 / UHS-I, 16GB+ with Raspberry Pi OS)

---

## 2. Hardware Connection & GPIO Pinout

The Kuman 3.5" HDMI Display-B connects to the Raspberry Pi 4 through two physical interfaces:
1. **Video:** Connected via the **Micro-HDMI to HDMI bridge** from Pi 4 Micro-HDMI 0 directly into the display's HDMI port.
2. **Power & Touch:** Mounted directly onto the first 26 pins of the Raspberry Pi 4's 40-pin GPIO header (Pins 1–26).

### 26-Pin GPIO Header Mapping (Power & XPT2046 Touch)

| Pin # | Raspberry Pi 4 Pin / GPIO | Signal Name | Function |
| :---: | :--- | :--- | :--- |
| **1** | Pin 1 (3.3V) | **3V3** | 3.3V Logic Supply for XPT2046 touch IC |
| **2** | Pin 2 (5V) | **5V_IN** | 5V Display logic & LED backlight power |
| **4** | Pin 4 (5V) | **5V_IN** | 5V Power (parallel rail) |
| **6** | Pin 6 (GND) | **GND** | System Ground |
| **9** | Pin 9 (GND) | **GND** | System Ground |
| **11**| Pin 11 (GPIO 17) | **NC / Reserved** | Not connected on HDMI-B model |
| **14**| Pin 14 (GND) | **GND** | System Ground |
| **19**| Pin 19 (GPIO 10 - MOSI0) | **TP_SI** | Touch Controller SPI Data In |
| **20**| Pin 20 (GND) | **GND** | System Ground |
| **21**| Pin 21 (GPIO 9 - MISO0) | **TP_SO** | Touch Controller SPI Data Out |
| **22**| Pin 22 (GPIO 25) | **TP_IRQ** | Touch Interrupt (active LOW on touch contact) |
| **23**| Pin 23 (GPIO 11 - SCLK0) | **TP_SCK** | Touch Controller SPI Clock |
| **24**| Pin 24 (GPIO 8 - CE0) | **NC / Reserved** | Alternate SPI Chip Select |
| **25**| Pin 25 (GND) | **GND** | System Ground |
| **26**| Pin 26 (GPIO 7 - CE1) | **TP_CS** | Touch Controller SPI Chip Select |

*(Pins 27–40 on the Raspberry Pi 4 GPIO header remain completely exposed and unencumbered for external peripherals or auxiliary sensors).*

---

## 3. Interaction Model (Touchscreen replacing Thumbwheel)

All tactile thumbwheel controls are now handled directly through the 480×320 touchscreen:

| Physical Thumbwheel (Old) | Touchscreen Equivalent (New) | Behavior in UI |
| :--- | :--- | :--- |
| **Thumbwheel Up / Down** | **Touch Drag / Swipe Up & Down** | Smooth inertial scrolling through app cards, checklist rows, or counter lists. |
| **Center Push (Click)** | **Direct Screen Tap** | Tap to toggle checkboxes, select buttons, confirm dialogs (`[ Yes ]` / `[ No ]`). |
| **Center Push (Long Hold)** | **Touch & Hold On-Screen PTT Button** | Touch-and-hold the dedicated microphone / action bar at the bottom of the screen to record voice; release to send. |

---

## 4. Raspberry Pi OS Display & Touch Configuration

To configure native 480×320 resolution and touch calibration on Raspberry Pi OS:

### Video Resolution (`/boot/firmware/config.txt` or `/boot/config.txt`)
Add the following HDMI timing block:
```ini
hdmi_force_hotplug=1
config_hdmi_boost=10
hdmi_group=2
hdmi_mode=87
hdmi_cvt=480 320 60 6 0 0 0
dtoverlay=ads7846,cs=1,penirq=25,penirq_pull=2,speed=50000,keep_vref_on=0,swapxy=0,pmax=255,xohms=150,xmin=200,xmax=3900,ymin=200,ymax=3900
```

### Alternatively, using the official LCD-show driver:
```bash
git clone https://github.com/goodtft/LCD-show.git
chmod -R 755 LCD-show
cd LCD-show/
sudo ./MPI3508-show
```
