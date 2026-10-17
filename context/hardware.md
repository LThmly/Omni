# Hardware

## Parts

- **Computer:** Raspberry Pi 3 Model B
- **Display:** 5" 800×480 HDMI LCD with an XPT2046 touch controller
  - Picture: HDMI, 800×480
  - Touch: resistive XPT2046 on the GPIO header, over SPI
- **Link:** Short HDMI cable from the Pi’s full-size HDMI port to the panel
- **Power:** Official 5.1V / 2.5A micro-USB supply for the Pi. The panel takes 5V and ground from the 40-pin header
- **Audio:** USB microphone, when that path is wired
- **Storage:** MicroSD with Raspberry Pi OS

The panel board sits on the Pi’s 40-pin header. HDMI carries the picture. The header carries power and the touchscreen. The app does not claim any other GPIO. USB ports stay free for a microphone.

## Connect

1. Seat the display on the 40-pin header.
2. HDMI from the Pi’s HDMI port into the display. That port is `HDMI-A-1`.
3. Power the Pi.

Stand the stack so the right edge of the landscape picture is up. The app is a 480×800 phone and turns itself onto the 800×480 glass.

## Touch

The XPT2046 is the touchscreen. After the overlay below, Raspberry Pi OS presents it as a pointer, and the phone treats a finger the way a phone does: tap, drag, and hold.

`firmware/demo.sh` writes this line into `/boot/firmware/config.txt` (on an older image that file is `/boot/config.txt`):

```
dtoverlay=ads7846,cs=1,penirq=25,penirq_pull=2,speed=50000,keep_vref_on=1,swapxy=0,pmax=255,xohms=150,xmin=200,xmax=3900,ymin=200,ymax=3900
```

`ads7846` is the driver the XPT2046 uses. This is the usual wiring for these 5" boards:

| Pi pin | Signal | Role |
| :--- | :--- | :--- |
| 19 (MOSI) | TP_SI | Touch data in |
| 21 (MISO) | TP_SO | Touch data out |
| 23 (SCLK) | TP_SCK | Touch clock |
| 26 (CE1) | TP_CS | Touch chip select |
| 22 (GPIO 25) | TP_IRQ | Touch interrupt |

If a finger dragged sideways moves the pointer up and down, change `swapxy=0` to `swapxy=1` and reboot. Do not set `display_rotate` or `lcd_rotate`. The app already turns the page, and a second rotation sends taps to the wrong control.

## Picture

`firmware/demo.sh` also appends this to the single existing line in `/boot/firmware/cmdline.txt`:

```
video=HDMI-A-1:800x480M@60
```

Reboot. If the image only fills part of the glass, use `video=HDMI-A-1:800x480MR@60` instead.

Guides that set `hdmi_group`, `hdmi_mode`, and `hdmi_cvt` in `config.txt` are for an older Raspberry Pi OS. The current image ignores those lines.

## Using it

A finger is the input. Tap a row, a button, or `[ Yes, create it ]`. Drag to scroll. Hold the talk bar at the bottom, then release. The simulator on a laptop uses the mouse for those same touches.
