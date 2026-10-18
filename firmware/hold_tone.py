#!/usr/bin/env python3
"""Play 440 Hz at full scale on GPIO 13 until Ctrl+C.

    cd ~/Omni
    python3 firmware/hold_tone.py
"""

import speaker


if __name__ == "__main__":
    try:
        speaker.hold_tone(440)
    except speaker.SpeakerError as error:
        raise SystemExit(str(error))
