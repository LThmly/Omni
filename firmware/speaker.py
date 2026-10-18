#!/usr/bin/env python3
"""Play Omni replies on the GPIO 13 PWM speaker.

BCM GPIO 13 is physical pin 33, the left channel after
`dtoverlay=audremap,pins_12_13`. GPIO 12 (pin 32) is the right channel.
A mono speaker on pin 33 still hears the voice because both channels
carry the same samples.

    python3 firmware/speaker.py --beep
    python3 firmware/speaker.py --say "Hello from Omni"
"""

from __future__ import annotations

import argparse
import array
import io
import json
import math
import os
import shutil
import subprocess
import sys
import threading
import urllib.error
import urllib.request
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RATE = 22050
VOICE_ID = "21m00Tcm4TlvDq8ikWAM"
_lock = threading.Lock()
_playback = None
_warned = False


class SpeakerError(Exception):
    """The speaker could not play this reply."""


def load_env():
    path = ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def tone(frequency=440, seconds=0.45, rate=RATE, volume=0.35, fade=0.02):
    """Signed 16-bit mono PCM. A short fade keeps a one-shot beep from clicking."""
    count = int(rate * seconds)
    fade_samples = int(rate * fade) if fade else 0
    samples = array.array("h")
    for index in range(count):
        envelope = 1.0
        if fade_samples:
            envelope = min(1.0, index / fade_samples, (count - index) / fade_samples)
        value = int(volume * envelope * 32767 * math.sin(2 * math.pi * frequency * index / rate))
        samples.append(max(-32767, min(32767, value)))
    return samples.tobytes()


def stereo_wav(mono, rate=RATE):
    """Put the same samples on left (GPIO 13) and right (GPIO 12)."""
    if len(mono) % 2:
        mono = mono[:-1]
    samples = array.array("h")
    samples.frombytes(mono)
    paired = array.array("h")
    for sample in samples:
        paired.append(sample)
        paired.append(sample)
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(paired.tobytes())
    return buffer.getvalue()


def pwm_device():
    """ALSA name of the Pi's analog PWM card, after audremap moves it to the header."""
    if not shutil.which("aplay"):
        return None
    try:
        listed = subprocess.run(
            ["aplay", "-l"], capture_output=True, text=True, timeout=3, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    card = None
    for line in listed.stdout.splitlines():
        lower = line.lower()
        if not line.startswith("card ") or "device " not in line:
            continue
        if any(name in lower for name in ("headphone", "bcm2835")):
            card = line.split(":", 1)[0].replace("card", "").strip()
    if card is None:
        return None
    return "plughw:%s,0" % card


def play_wav(wav_bytes, device=None):
    """Play one clip. A newer clip replaces one that is still running."""
    global _playback
    player = shutil.which("aplay")
    if not player:
        raise SpeakerError("aplay is not installed. On the Pi: sudo apt install alsa-utils")
    chosen = pwm_device() if device is None else device
    if chosen is None and sys.platform.startswith("linux"):
        raise SpeakerError(
            "PWM audio is not on the header. Run sh firmware/demo.sh and let the Pi reboot once."
        )
    path = Path("/tmp/omni-speaker.wav")
    path.write_bytes(wav_bytes)
    command = [player, "-q"]
    if chosen:
        command.extend(["-D", chosen])
    command.append(str(path))
    with _lock:
        previous = _playback
        if previous is not None and previous.poll() is None:
            previous.terminate()
        _playback = subprocess.Popen(command)
        current = _playback
    try:
        current.wait(timeout=120)
    except subprocess.TimeoutExpired:
        current.kill()
        raise SpeakerError("Playback took too long.") from None
    if current.returncode not in (0, -15, None):
        raise SpeakerError("aplay exited with status %s." % current.returncode)


def fetch_speech(text, key, voice_id, model):
    request = urllib.request.Request(
        "https://api.elevenlabs.io/v1/text-to-speech/%s?output_format=pcm_22050" % voice_id,
        data=json.dumps({"text": text, "model_id": model}).encode(),
        headers={
            "xi-api-key": key,
            "Content-Type": "application/json",
            "Accept": "application/octet-stream",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            audio = response.read()
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")[:300]
        print("ElevenLabs %s: %s" % (error.code, detail), file=sys.stderr)
        raise SpeakerError("ElevenLabs returned HTTP %s." % error.code) from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise SpeakerError("Could not reach ElevenLabs.") from error
    if len(audio) < 2:
        raise SpeakerError("ElevenLabs returned no audio.")
    return audio


def speak(text):
    """Say one reply on the speaker. Returns immediately; playback is in the background."""
    text = " ".join((text or "").split())
    if not text or os.environ.get("OMNI_SPEAK") == "0":
        return
    threading.Thread(target=_speak, args=(text[:1200],), daemon=True).start()


def _speak(text):
    global _warned
    try:
        drive_gpio_low(21)
        if not shutil.which("aplay"):
            return
        load_env()
        key = os.environ.get("ELEVENLABS_API_KEY", "").strip()
        if not key:
            if not _warned:
                _warned = True
                print("Speaker: set ELEVENLABS_API_KEY in .env to speak replies.", flush=True)
            return
        voice = os.environ.get("ELEVENLABS_VOICE_ID", VOICE_ID).strip() or VOICE_ID
        model = os.environ.get("ELEVENLABS_MODEL", "eleven_flash_v2_5").strip() or "eleven_flash_v2_5"
        play_wav(stereo_wav(fetch_speech(text, key, voice, model)))
    except SpeakerError as error:
        print("Speaker: %s" % error, flush=True)


def drive_gpio_low(pin=21):
    """Hold a BCM GPIO as an output low. The Voice HAT overlay can reclaim it later."""
    for tool, args in (
        ("pinctrl", ["set", str(pin), "op", "dl"]),
        ("raspi-gpio", ["set", str(pin), "op", "dl"]),
    ):
        binary = shutil.which(tool)
        if not binary:
            continue
        subprocess.run([binary, *args], capture_output=True, timeout=3, check=False)
        return


def raise_volume(device):
    """Turn the PWM card all the way up. A quiet control hides a working pin."""
    mixer = shutil.which("amixer")
    if not mixer or not device or not device.startswith("plughw:"):
        return
    card = device.split(":", 1)[1].split(",", 1)[0]
    for control in ("PCM", "Headphone"):
        subprocess.run(
            [mixer, "-c", card, "sset", control, "100%"],
            capture_output=True, timeout=3, check=False,
        )


def stereo_pcm(mono):
    """Left (GPIO 13) and right (GPIO 12) carry the same sample."""
    if len(mono) % 2:
        mono = mono[:-1]
    samples = array.array("h")
    samples.frombytes(mono)
    paired = array.array("h")
    for sample in samples:
        paired.append(sample)
        paired.append(sample)
    return paired.tobytes()


def hold_tone(frequency=100):
    """Play one tone at full scale until Ctrl+C."""
    player = shutil.which("aplay")
    if not player:
        raise SpeakerError("aplay is not installed. On the Pi: sudo apt install alsa-utils")
    chosen = pwm_device()
    if chosen is None and sys.platform.startswith("linux"):
        raise SpeakerError(
            "PWM audio is not on the header. Run sh firmware/demo.sh and let the Pi reboot once."
        )
    drive_gpio_low(21)
    raise_volume(chosen)
    command = [player, "-q", "-f", "S16_LE", "-r", str(RATE), "-c", "2", "-t", "raw"]
    if chosen:
        command[1:1] = ["-D", chosen]
    chunk = stereo_pcm(tone(frequency, seconds=1, volume=1, fade=0))
    print("%s Hz at full scale. Ctrl+C stops it." % frequency, flush=True)
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        while True:
            process.stdin.write(chunk)
            process.stdin.flush()
            if process.poll() is not None:
                raise SpeakerError("aplay stopped (status %s)." % process.returncode)
    except KeyboardInterrupt:
        print("\nStopped.", flush=True)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()


def beep():
    drive_gpio_low(21)
    play_wav(stereo_wav(tone()))


def main():
    parser = argparse.ArgumentParser(description="Test the GPIO 13 speaker or speak one line.")
    parser.add_argument("--beep", action="store_true", help="Play a short tone on the PWM speaker.")
    parser.add_argument("--hold", action="store_true", help="Play 440 Hz at full scale until Ctrl+C.")
    parser.add_argument("--say", help="Speak this line with ElevenLabs.")
    args = parser.parse_args()
    if not args.beep and not args.hold and not args.say:
        parser.error("Pass --beep, --hold, or --say.")
    try:
        if args.beep:
            beep()
        if args.hold:
            hold_tone(440)
        if args.say:
            os.environ["OMNI_SPEAK"] = "1"
            _speak(args.say)
    except SpeakerError as error:
        raise SystemExit(str(error))


if __name__ == "__main__":
    main()
