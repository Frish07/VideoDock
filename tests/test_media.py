import subprocess
import tempfile
import unittest
from pathlib import Path

from videodock.core import find_ffmpeg
from videodock.media import ensure_compatible_mp4


class MP4CompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.ffmpeg = find_ffmpeg()
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.source = Path(directory) / "Проверка.mp4"

    def run_ffmpeg(self, *args):
        return subprocess.run(
            [str(self.ffmpeg), "-hide_banner", "-nostdin", *map(str, args)],
            capture_output=True, encoding="utf-8", errors="replace", check=True,
        )

    def make_mp4(self, video_codec="libx264", audio_codec="aac", channels=2):
        audio_args = []
        if audio_codec:
            audio_args = ["-f", "lavfi", "-i", "sine=frequency=500:sample_rate=48000:duration=0.5",
                          "-c:a", audio_codec, "-ac", str(channels)]
        self.run_ffmpeg("-loglevel", "error",
                        "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=24:duration=0.5",
                        *audio_args, "-c:v", video_codec, "-pix_fmt", "yuv420p", self.source)

    def stream_hash(self, stream):
        return self.run_ffmpeg("-loglevel", "error", "-i", self.source, "-map", stream,
                               "-c", "copy", "-f", "streamhash", "-").stdout

    def decoded_streams(self):
        return self.run_ffmpeg("-i", self.source, "-map", "0:v:0", "-map", "0:a:0",
                               "-xerror", "-f", "null", "-").stderr.partition("Stream mapping:")[0]

    def test_opus_becomes_aac_without_reencoding_h264(self):
        self.make_mp4(audio_codec="libopus")
        original_video = self.stream_hash("0:v:0")
        self.assertIn("Audio: opus", self.decoded_streams())
        ensure_compatible_mp4(self.source, self.ffmpeg)
        self.assertRegex(self.decoded_streams(), r"Audio: aac \(LC\).*, 48000 Hz, stereo,")
        self.assertEqual(self.stream_hash("0:v:0"), original_video)

    def test_vp9_becomes_h264_without_reencoding_aac(self):
        self.make_mp4(video_codec="libvpx-vp9")
        original_audio = self.stream_hash("0:a:0")
        ensure_compatible_mp4(self.source, self.ffmpeg)
        self.assertRegex(self.decoded_streams(), r"Video: h264 .*yuv420p.*160x90")
        self.assertEqual(self.stream_hash("0:a:0"), original_audio)

    def test_compatible_file_is_untouched(self):
        self.make_mp4(channels=1)
        original = self.source.read_bytes()
        ensure_compatible_mp4(self.source, self.ffmpeg)
        self.assertEqual(self.source.read_bytes(), original)

    def test_surround_audio_is_downmixed_to_stereo(self):
        self.make_mp4(channels=6)
        ensure_compatible_mp4(self.source, self.ffmpeg)
        self.assertRegex(self.decoded_streams(), r"Audio: aac \(LC\).*, 48000 Hz, stereo,")

    def test_missing_audio_fails_before_replacing_original(self):
        self.make_mp4(audio_codec=None)
        original = self.source.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "Не удалось проверить видео и звук"):
            ensure_compatible_mp4(self.source, self.ffmpeg)
        self.assertEqual(self.source.read_bytes(), original)
