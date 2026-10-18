"""Speaker clip layout and the ElevenLabs request. No device and no network."""

import io
import os
import unittest
import wave
from unittest.mock import patch

import speaker


class Reply:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return self.payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class SpeakerTest(unittest.TestCase):
    def test_tone_is_quiet_at_both_ends(self):
        pcm = speaker.tone(seconds=0.1)
        self.assertEqual(len(pcm) % 2, 0)
        self.assertEqual(pcm[:2], b"\x00\x00")
        last = int.from_bytes(pcm[-2:], "little", signed=True)
        self.assertLess(abs(last), 1000)

    def test_hold_tone_is_full_scale_100_hz(self):
        pcm = speaker.tone(100, seconds=1, volume=1, fade=0)
        self.assertEqual(len(pcm), speaker.RATE * 2)
        peak = max(abs(int.from_bytes(pcm[i:i + 2], "little", signed=True)) for i in range(0, len(pcm), 2))
        self.assertGreater(peak, 30000)

    def test_speech_boost_reaches_full_scale_and_clips(self):
        boosted = speaker.amplify(b"\x00\x01\xff\x7f", 8)
        self.assertEqual(boosted[:2], b"\x00\x08")
        self.assertEqual(boosted[2:], b"\xff\x7f")

    def test_stereo_copies_the_sample_onto_gpio_13(self):
        wav_bytes = speaker.stereo_wav(b"\x01\x00\x02\x00")
        with wave.open(io.BytesIO(wav_bytes)) as handle:
            self.assertEqual(handle.getnchannels(), 2)
            self.assertEqual(handle.getframerate(), speaker.RATE)
            frames = handle.readframes(handle.getnframes())
        # Left sample, then right sample. GPIO 13 is the left channel.
        self.assertEqual(frames, b"\x01\x00\x01\x00\x02\x00\x02\x00")

    def test_missing_key_does_not_call_elevenlabs(self):
        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": ""}, clear=False):
            with patch.object(speaker, "load_env"):
                with patch.object(speaker.shutil, "which", return_value="/usr/bin/aplay"):
                    with patch.object(speaker, "fetch_speech") as fetch:
                        speaker._speak("Hello")
        fetch.assert_not_called()

    def test_speech_request_uses_pcm_and_plays_both_channels(self):
        played = {}

        def opener(request, timeout=0):
            played["url"] = request.full_url
            played["key"] = request.get_header("Xi-api-key")
            return Reply(b"\x10\x00\x20\x00")

        def capture(wav_bytes, device=None):
            played["wav"] = wav_bytes

        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "test-key", "ELEVENLABS_VOICE_ID": "voice", "SPEAKER_GAIN": "1"}, clear=False):
            with patch.object(speaker, "load_env"):
                with patch.object(speaker.shutil, "which", return_value="/usr/bin/aplay"):
                    with patch.object(speaker.urllib.request, "urlopen", opener):
                        with patch.object(speaker, "play_wav", capture):
                            speaker._speak("Hello there")
        self.assertIn("voice", played["url"])
        self.assertIn("output_format=pcm_22050", played["url"])
        self.assertEqual(played["key"], "test-key")
        with wave.open(io.BytesIO(played["wav"])) as handle:
            self.assertEqual(handle.getnchannels(), 2)
            self.assertEqual(handle.readframes(2), b"\x10\x00\x10\x00\x20\x00\x20\x00")


if __name__ == "__main__":
    unittest.main()
