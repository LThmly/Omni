#!/usr/bin/env python3
"""Omni Touchscreen Bringup & Diagnostic Utility for Raspberry Pi.

Tests the XPT2046 / ADS7846 touchscreen on the 5" 800x480 HDMI LCD.

Usage:
    # Run the interactive visual GUI test (default on desktop)
    python3 firmware/bringup/test_display_touch.py

    # Monitor raw /dev/input events in terminal
    python3 firmware/bringup/test_display_touch.py --cli

    # Check configuration files & hardware status
    python3 firmware/bringup/test_display_touch.py --check

    # Low-level direct SPI test (bypassing Linux input subsystem)
    python3 firmware/bringup/test_display_touch.py --spi
"""

from __future__ import annotations

import argparse
import glob
import os
import struct
import sys
import time
from pathlib import Path


def find_touch_device() -> tuple[str, str] | None:
    """Find the touchscreen event device in /dev/input."""
    # 1. Check /proc/bus/input/devices for ADS7846 or Touchscreen
    proc_devices = Path("/proc/bus/input/devices")
    if proc_devices.exists():
        content = proc_devices.read_text(errors="replace")
        blocks = content.strip().split("\n\n")
        for block in blocks:
            name_line = ""
            event_name = ""
            for line in block.splitlines():
                if line.startswith("N: Name="):
                    name_line = line.split("=", 1)[1].strip('"\n\r ')
                elif "Handlers=" in line and "event" in line:
                    for part in line.split():
                        if part.startswith("event"):
                            event_name = part
            if event_name and any(k in name_line.lower() for k in ("ads7846", "touch", "xpt2046", "touchscreen")):
                dev_path = f"/dev/input/{event_name}"
                if os.path.exists(dev_path):
                    return dev_path, name_line

    # 2. Check /dev/input/by-path or by-id
    by_path = glob.glob("/dev/input/by-path/*touch*") or glob.glob("/dev/input/by-path/*ads7846*")
    if by_path:
        real = os.path.realpath(by_path[0])
        return real, "ADS7846 Touchscreen (via by-path)"

    # 3. Check event nodes
    for node in sorted(glob.glob("/dev/input/event*")):
        try:
            # Check device name via sysfs
            ev_name = os.path.basename(node)
            sys_name_path = Path(f"/sys/class/input/{ev_name}/device/name")
            if sys_name_path.exists():
                name = sys_name_path.read_text().strip()
                if any(k in name.lower() for k in ("ads7846", "touch", "xpt2046")):
                    return node, name
        except Exception:
            continue

    # Fallback to the first available event device if any
    all_events = sorted(glob.glob("/dev/input/event*"))
    if all_events:
        return all_events[0], "Fallback Input Device"

    return None


def run_system_check() -> None:
    """Validate system configuration for XPT2046 touch on Raspberry Pi."""
    print("=" * 60)
    print("  Omni Touchscreen Diagnostic Check")
    print("=" * 60)

    # 1. Check config.txt for ads7846 overlay
    config_paths = [Path("/boot/firmware/config.txt"), Path("/boot/config.txt")]
    config_file = next((p for p in config_paths if p.exists()), None)
    
    if config_file:
        print(f"[✓] Found config: {config_file}")
        content = config_file.read_text(errors="replace")
        has_overlay = "dtoverlay=ads7846" in content
        has_spi = "dtparam=spi=on" in content

        if has_overlay:
            print("    [✓] dtoverlay=ads7846 is configured.")
            for line in content.splitlines():
                if "ads7846" in line and not line.strip().startswith("#"):
                    print(f"        Line: {line.strip()}")
        else:
            print("    [!] WARNING: 'dtoverlay=ads7846' not found in config.")
            print("        Add the overlay to enable the touchscreen driver:")
            print("        dtoverlay=ads7846,cs=1,penirq=25,penirq_pull=2,speed=50000,keep_vref_on=1,swapxy=0,pmax=255,xohms=150,xmin=200,xmax=3900,ymin=200,ymax=3900")

        if has_spi:
            print("    [✓] dtparam=spi=on is enabled.")
        else:
            print("    [i] Note: 'dtparam=spi=on' is recommended for SPI access.")
    else:
        print("[!] Not on Raspberry Pi OS or config.txt not found.")

    # 2. Check SPI devices
    spidev1 = Path("/dev/spidev0.1")
    if spidev1.exists():
        print(f"[✓] SPI device exists: {spidev1}")
    else:
        print(f"[i] {spidev1} not visible (normal if kernel driver ads7846 claimed it).")

    # 3. Check Input subsystem
    touch = find_touch_device()
    if touch:
        dev_path, dev_name = touch
        print(f"[✓] Touchscreen device found: {dev_path} ({dev_name})")
        if os.access(dev_path, os.R_OK):
            print("    [✓] Device is readable by current user.")
        else:
            print(f"    [!] Device is NOT readable. Run with 'sudo' or add udev rule:")
            print(f"        sudo chmod a+r {dev_path}")
    else:
        print("[!] No touchscreen device detected in /dev/input.")
        print("    Ensure the display is firmly seated on the 40-pin header")
        print("    and the Pi has been rebooted after adding the dtoverlay.")

    # 4. Check display resolution in cmdline.txt
    cmdline_paths = [Path("/boot/firmware/cmdline.txt"), Path("/boot/cmdline.txt")]
    cmdline_file = next((p for p in cmdline_paths if p.exists()), None)
    if cmdline_file:
        cmd_content = cmdline_file.read_text(errors="replace")
        if "800x480" in cmd_content:
            print(f"[✓] 800x480 video mode found in {cmdline_file.name}")
        else:
            print(f"[!] 'video=HDMI-A-1:800x480M@60' not in {cmdline_file.name}")

    print("=" * 60)


def run_cli_monitor(device_path: str) -> None:
    """Stream live touch events from the Linux event device."""
    print(f"Opening {device_path} for touch events...")
    print("Touch the screen! Press Ctrl+C to stop.")
    print("-" * 55)

    # Event types in Linux input.h
    EV_SYN = 0x00
    EV_KEY = 0x01
    EV_ABS = 0x03

    ABS_X = 0x00
    ABS_Y = 0x01
    ABS_PRESSURE = 0x18
    BTN_TOUCH = 0x14A

    x, y, pressure = 0, 0, 0
    is_down = False

    # Check architecture to format struct input_event
    # 64-bit: 2x 64-bit int (timeval) + unsigned short + unsigned short + signed int (24 bytes)
    # 32-bit: 2x 32-bit int (timeval) + unsigned short + unsigned short + signed int (16 bytes)
    is_64bit = struct.calcsize("P") == 8
    event_fmt = "qqHHi" if is_64bit else "iiHHi"
    event_size = struct.calcsize(event_fmt)

    try:
        fd = os.open(device_path, os.O_RDONLY)
    except PermissionError:
        print(f"Permission denied reading {device_path}. Run with sudo:")
        print(f"  sudo python3 firmware/bringup/test_display_touch.py --cli")
        return

    try:
        while True:
            data = os.read(fd, event_size)
            if not data or len(data) < event_size:
                continue

            sec, usec, ev_type, ev_code, ev_value = struct.unpack(event_fmt, data[:event_size])

            if ev_type == EV_KEY and ev_code == BTN_TOUCH:
                is_down = bool(ev_value)
                status = "DOWN ▼" if is_down else "UP   ▲"
                print(f"[{status}] Touch State: {is_down} (X={x:4d}, Y={y:4d}, Pressure={pressure:4d})")
            elif ev_type == EV_ABS:
                if ev_code == ABS_X:
                    x = ev_value
                elif ev_code == ABS_Y:
                    y = ev_value
                elif ev_code == ABS_PRESSURE:
                    pressure = ev_value
            elif ev_type == EV_SYN:
                if is_down:
                    # Print coordinate update during drag
                    print(f"  --> Drag: X={x:4d} | Y={y:4d} | Pressure={pressure:4d}", end="\r")
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        os.close(fd)


def run_gui_test() -> None:
    """Launch full-screen visual touch test using Tkinter."""
    try:
        import tkinter as tk
    except ImportError:
        print("Tkinter is not installed. To run the visual GUI test on the Pi:")
        print("  sudo apt-get install -y python3-tk")
        print("Falling back to CLI monitor...")
        touch = find_touch_device()
        if touch:
            run_cli_monitor(touch[0])
        else:
            run_system_check()
        return

    root = tk.Tk()
    root.title("Omni Touchscreen Diagnostic")
    root.configure(bg="#090b10")

    # Set window size matching LCD (800x480)
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    root.geometry(f"{screen_w}x{screen_h}+0+0")
    root.attributes("-fullscreen", True)

    canvas = tk.Canvas(root, bg="#090b10", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    # Info Bar
    info_text = canvas.create_text(
        20, 20,
        text="Omni Touch Test | Touch to draw | [R] Rotate 90° | [C] Clear | [Q/ESC] Quit",
        fill="#94a3b8", font=("Helvetica", 11, "bold"), anchor="nw"
    )

    coord_text = canvas.create_text(
        20, 50,
        text="X: 0 | Y: 0 | Touches: 0",
        fill="#00f0ff", font=("Courier", 13, "bold"), anchor="nw"
    )

    last_x, last_y = None, None
    touch_count = 0
    targets_hit = set()

    # Draw 5 calibration target circles
    targets = [
        ("TL (Top-Left)", int(screen_w * 0.1), int(screen_h * 0.15)),
        ("TR (Top-Right)", int(screen_w * 0.9), int(screen_h * 0.15)),
        ("BL (Bottom-Left)", int(screen_w * 0.1), int(screen_h * 0.85)),
        ("BR (Bottom-Right)", int(screen_w * 0.9), int(screen_h * 0.85)),
        ("Center", int(screen_w * 0.5), int(screen_h * 0.5)),
    ]

    for label, tx, ty in targets:
        canvas.create_oval(tx - 24, ty - 24, tx + 24, ty + 24, outline="#334155", width=2, dash=(4, 4), tags=f"t_{label}")
        canvas.create_oval(tx - 5, ty - 5, tx + 5, ty + 5, fill="#00f0ff", outline="", tags=f"dot_{label}")
        canvas.create_text(tx, ty + 30, text=label, fill="#64748b", font=("Helvetica", 9), tags=f"lbl_{label}")

    def on_touch_down(event):
        nonlocal last_x, last_y, touch_count
        last_x, last_y = event.x, event.y
        touch_count += 1
        canvas.itemconfig(coord_text, text=f"X: {event.x:4d} | Y: {event.y:4d} | Touches: {touch_count}")
        
        # Draw touch ripple
        r = 12
        canvas.create_oval(event.x - r, event.y - r, event.x + r, event.y + r, fill="#00f0ff", outline="#38bdf8", width=2, tags="trail")
        
        # Check target collisions
        for label, tx, ty in targets:
            dist = ((event.x - tx) ** 2 + (event.y - ty) ** 2) ** 0.5
            if dist < 32:
                targets_hit.add(label)
                canvas.itemconfig(f"t_{label}", outline="#10b981", fill="#064e3b", width=3, dash=())
                canvas.itemconfig(f"dot_{label}", fill="#10b981")
                canvas.itemconfig(f"lbl_{label}", fill="#10b981", text=f"{label} [✓ HIT]")

    def on_touch_move(event):
        nonlocal last_x, last_y
        if last_x is not None and last_y is not None:
            canvas.create_line(last_x, last_y, event.x, event.y, fill="#4e8cff", width=4, capstyle=tk.ROUND, smooth=True, tags="trail")
        last_x, last_y = event.x, event.y
        canvas.itemconfig(coord_text, text=f"X: {event.x:4d} | Y: {event.y:4d} | Touches: {touch_count}")

    def on_touch_up(event):
        nonlocal last_x, last_y
        last_x, last_y = None, None

    def clear_canvas(event=None):
        nonlocal targets_hit
        canvas.delete("trail")
        targets_hit.clear()
        for label, tx, ty in targets:
            canvas.itemconfig(f"t_{label}", outline="#334155", fill="", width=2, dash=(4, 4))
            canvas.itemconfig(f"dot_{label}", fill="#00f0ff")
            canvas.itemconfig(f"lbl_{label}", fill="#64748b", text=label)

    canvas.bind("<Button-1>", on_touch_down)
    canvas.bind("<B1-Motion>", on_touch_move)
    canvas.bind("<ButtonRelease-1>", on_touch_up)

    root.bind("<Key-c>", clear_canvas)
    root.bind("<Key-C>", clear_canvas)
    root.bind("<Key-q>", lambda e: root.destroy())
    root.bind("<Key-Q>", lambda e: root.destroy())
    root.bind("<Escape>", lambda e: root.destroy())

    print("Running GUI Touch Test. Tap the targets on your 5\" LCD.")
    root.mainloop()


def run_raw_spi_test() -> None:
    """Low-level SPI hardware test talking directly to XPT2046 IC over SPI0 CE1."""
    print("Testing direct SPI communication with XPT2046...")
    try:
        import spidev
    except ImportError:
        print("spidev not found. Install with: sudo apt-get install -y python3-spidev")
        return

    spi = spidev.SpiDev()
    try:
        # Bus 0, Device 1 = SPI0_CE1 (Pin 26)
        spi.open(0, 1)
        spi.max_speed_hz = 500000
        spi.mode = 0
    except Exception as exc:
        print(f"Could not open SPI device (0, 1): {exc}")
        print("Note: If the Linux ads7846 driver is active, it controls CE1 exclusively.")
        return

    print("Reading XPT2046 ADC over SPI (Bus 0, CE1). Touch the screen! Press Ctrl+C to stop.")
    try:
        while True:
            # Command 0xD0: Read X-channel (12-bit, differential)
            # Command 0x90: Read Y-channel (12-bit, differential)
            # Command 0xB0: Read Z1 (Pressure)
            resp_x = spi.xfer2([0xD0, 0x00, 0x00])
            raw_x = ((resp_x[1] << 8) | resp_x[2]) >> 3

            resp_y = spi.xfer2([0x90, 0x00, 0x00])
            raw_y = ((resp_y[1] << 8) | resp_y[2]) >> 3

            resp_z = spi.xfer2([0xB0, 0x00, 0x00])
            raw_z = ((resp_z[1] << 8) | resp_z[2]) >> 3

            if raw_z > 100:  # Touch detected
                print(f"Touch Detected: Raw X={raw_x:4d} | Raw Y={raw_y:4d} | Pressure={raw_z:4d}")
            time.sleep(0.05)
    except KeyboardInterrupt:
        print("\nStopped SPI test.")
    finally:
        spi.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Omni Touchscreen Diagnostic Utility")
    parser.add_argument("--cli", action="store_true", help="Monitor raw events from /dev/input in terminal")
    parser.add_argument("--check", action="store_true", help="Check config.txt and driver setup")
    parser.add_argument("--spi", action="store_true", help="Run low-level SPI diagnostic test")
    parser.add_argument("--device", default=None, help="Explicit /dev/input/event* path")
    args = parser.parse_args()

    if args.check:
        run_system_check()
        return

    if args.spi:
        run_raw_spi_test()
        return

    touch = find_touch_device()
    dev_path = args.device or (touch[0] if touch else None)

    if args.cli:
        if not dev_path:
            print("No touchscreen input device found.")
            run_system_check()
            return
        run_cli_monitor(dev_path)
    else:
        # Default mode: GUI test if display session exists, else CLI
        if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
            run_gui_test()
        else:
            print("No graphical display found. Running CLI event monitor...")
            if dev_path:
                run_cli_monitor(dev_path)
            else:
                run_system_check()


if __name__ == "__main__":
    main()
