#!/usr/bin/env python3
"""Serve the Omni phone.

On a laptop:

    python3 firmware/shell.py

On the Pi, fullscreen, reopening if the window is closed:

    python3 firmware/shell.py --kiosk

Once, so every login opens it:

    python3 firmware/install.sh

Quit with Ctrl+Shift+Q, or `python3 firmware/shell.py --stop`.
"""

from __future__ import annotations

import argparse
import fcntl
import os
import shutil
import signal
import subprocess
import sys
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PID_PATH = Path.home() / ".omni" / "shell.pid"
BROWSERS = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable")

stop = threading.Event()
server = None
browser = None
lock_handle = None


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/__omni/quit":
            self.send_error(404)
            return
        self.send_response(204)
        self.end_headers()
        threading.Thread(target=request_quit, daemon=True).start()

    def do_GET(self):
        if self.path.split("?", 1)[0] == "/__omni/quit":
            self.do_POST()
            return
        super().do_GET()


def pi_model():
    path = Path("/proc/device-tree/model")
    if not path.exists():
        return ""
    return path.read_bytes().decode("utf-8", "replace").strip("\x00").strip()


def graphical_session():
    return bool(os.environ.get("WAYLAND_DISPLAY") or os.environ.get("DISPLAY"))


def request_quit():
    stop.set()
    if browser is not None and browser.poll() is None:
        browser.terminate()
    if server is not None:
        server.shutdown()


def launch_browser(url):
    if not graphical_session():
        print("No desktop session. Open a terminal on the Pi desktop and run this again.")
        print("The UI is still being served at", url)
        return None
    name = next((item for item in BROWSERS if shutil.which(item)), None)
    if name is None:
        print("Chromium is not installed. On the Pi: sudo apt install chromium")
        print("The UI is still being served at", url)
        return None
    cmd = [
        name,
        "--kiosk",
        "--noerrdialogs",
        "--disable-infobars",
        "--disable-translate",
        "--disable-features=TranslateUI",
        "--no-first-run",
        "--disable-session-crashed-bubble",
        "--check-for-update-interval=31536000",
        "--autoplay-policy=no-user-gesture-required",
    ]
    if os.environ.get("WAYLAND_DISPLAY"):
        cmd.append("--ozone-platform=wayland")
    cmd.append(url)
    print("kiosk:", " ".join(cmd))
    return subprocess.Popen(cmd)


def kiosk_loop(url):
    global browser
    while not stop.is_set():
        browser = launch_browser(url)
        if browser is None:
            return
        while browser.poll() is None and not stop.is_set():
            try:
                browser.wait(timeout=0.4)
            except subprocess.TimeoutExpired:
                pass
        if stop.is_set():
            if browser.poll() is None:
                browser.terminate()
            return
        print("kiosk closed; opening it again")
        time.sleep(0.5)


def hold_lock():
    global lock_handle
    PID_PATH.parent.mkdir(parents=True, exist_ok=True)
    lock_handle = open(PID_PATH, "a+")
    try:
        fcntl.flock(lock_handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_handle.seek(0)
        existing = lock_handle.read().strip() or "unknown"
        print("Omni is already running (pid %s)." % existing)
        print("Quit it with: python3 firmware/shell.py --stop")
        sys.exit(0)
    lock_handle.seek(0)
    lock_handle.truncate()
    lock_handle.write(str(os.getpid()))
    lock_handle.flush()


def stop_running():
    if not PID_PATH.exists():
        print("Omni is not running.")
        return
    text = PID_PATH.read_text().strip()
    if not text.isdigit():
        print("Omni is not running.")
        return
    try:
        os.kill(int(text), signal.SIGTERM)
    except OSError as exc:
        print("Could not stop pid %s: %s" % (text, exc))
        return
    print("Stopped Omni.")


def main():
    global server
    parser = argparse.ArgumentParser(description="Serve the Omni phone.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--kiosk", action="store_true", help="Open fullscreen and keep it open.")
    parser.add_argument(
        "--turn",
        choices=("right", "left"),
        default="right",
        help="Which way the portrait UI turns onto the landscape panel.",
    )
    parser.add_argument("--stop", action="store_true", help="Quit a running shell.")
    args = parser.parse_args()

    if args.stop:
        stop_running()
        return

    hold_lock()
    model = pi_model()
    if model:
        print(model)

    try:
        server = ThreadingHTTPServer((args.host, args.port), Handler)
    except OSError as exc:
        print("Could not listen on %s:%s: %s" % (args.host, args.port, exc), file=sys.stderr)
        sys.exit(1)

    url = "http://127.0.0.1:%s/sim/" % args.port
    if args.kiosk:
        url += "?kiosk=1"
        if args.turn == "left":
            url += "&turn=left"
    print("Omni UI at %s" % url)
    if args.kiosk:
        print("Stays up until Ctrl+Shift+Q, or: python3 firmware/shell.py --stop")
    else:
        print("Ctrl-C stops the server.")

    if args.kiosk:
        threading.Thread(target=kiosk_loop, args=(url,), daemon=True).start()

    def handle_stop(signum, frame):
        threading.Thread(target=request_quit, daemon=True).start()

    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)
    try:
        server.serve_forever()
    finally:
        stop.set()
        if browser is not None and browser.poll() is None:
            browser.terminate()
        server.server_close()


if __name__ == "__main__":
    main()
