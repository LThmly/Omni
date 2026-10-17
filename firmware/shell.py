#!/usr/bin/env python3
"""Open the Omni phone.

The window is drawn with pygame. On a laptop it is a 480×800 portrait.
On the Pi, `--kiosk` turns it onto the 800×480 glass.

    python3 firmware/shell.py
    python3 firmware/shell.py --kiosk
    python3 firmware/shell.py --stop
"""

from phone import main

if __name__ == "__main__":
    main()
