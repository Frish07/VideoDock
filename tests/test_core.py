import tempfile
import unittest
from pathlib import Path

from videodock.core import (DownloadRequest, available_heights, format_selector,
                            format_time, normalize_url, parse_time, unique_destination,
                            validate_range)


class InputTests(unittest.TestCase):
    def test_video_urls_normalize_and_drop_playlist(self):
        expected = "https://www.youtube.com/watch?v=BaW_jenozKc"
        for value in ["youtu.be/BaW_jenozKc?t=42", "https://www.youtube.com/watch?v=BaW_jenozKc&list=test",
                      "https://youtube.com/shorts/BaW_jenozKc", "https://m.youtube.com/watch?v=BaW_jenozKc",
                      "https://music.youtube.com/watch?v=BaW_jenozKc"]:
            with self.subTest(value=value):
                self.assertEqual(normalize_url(value), expected)

    def test_reject_non_video_and_misleading_hosts(self):
        for value in ["", "https://youtube.com.evil.example/watch?v=BaW_jenozKc",
                      "https://example.com/BaW_jenozKc", "file:///test", "https://youtube.com/playlist?list=123",
                      "https://youtube.com/watch?v=123", "https://user:pass@youtube.com/watch?v=BaW_jenozKc"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_url(value)

    def test_timestamp_parsing(self):
        self.assertEqual(parse_time("1:45"), 105)
        self.assertEqual(parse_time("01:02:30.5"), 3750.5)
        self.assertEqual(parse_time("90,25"), 90.25)
        self.assertIsNone(parse_time(""))
        for value in ["1:99", "1:60:00", "-10", "NaN", "1:2:3:4", "1.2:20"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                parse_time(value)

    def test_range_validation(self):
        self.assertEqual(validate_range("1:45", "6:50", 600), (105, 410))
        self.assertEqual(validate_range("", "", 600), (0, None))
        for start, end in [("4:00", "3:00"), ("3:00", "3:00"), ("10:00", ""), ("", "10:01")]:
            with self.subTest(start=start, end=end), self.assertRaises(ValueError):
                validate_range(start, end, 600)

    def test_disabled_trim_ignores_old_values(self):
        request = DownloadRequest("https://youtu.be/BaW_jenozKc", "output", trim=False, start="bad", end="bad")
        self.assertEqual(request.validate(10), (0, None))

    def test_invalid_audio_container_rejected(self):
        with self.assertRaises(ValueError):
            DownloadRequest("https://youtu.be/BaW_jenozKc", "out", audio=True, container="mp4").validate()

    def test_real_formats_only(self):
        self.assertEqual(available_heights([
            {"height": 144, "vcodec": "av1"}, {"height": 1080, "vcodec": "vp9"},
            {"height": 1080, "vcodec": "avc"}, {"height": 2160, "vcodec": "none"},
            {"height": 4320, "vcodec": "av1", "has_drm": True}]), [1080, 144])

    def test_quality_limit_applies_to_fallback(self):
        selector = format_selector(144, "mp4", False)
        self.assertIn("bestvideo[height<=144]", selector)
        self.assertTrue(selector.endswith("/best[height<=144]"))
        self.assertEqual(format_selector(None, "mp3", True), "bestaudio/best")
        self.assertIn("ext=webm", format_selector(1080, "webm", False))

    def test_preserve_existing_file_names(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            (path / "video.mp4").write_bytes(b"original")
            (path / "video (2).mp4").touch()
            self.assertEqual(unique_destination(path, "video.mp4").name, "video (3).mp4")
            self.assertEqual((path / "video.mp4").read_bytes(), b"original")

    def test_long_duration_format(self):
        self.assertEqual(format_time(105), "1:45")
        self.assertEqual(format_time(3750), "1:02:30")


if __name__ == "__main__":
    unittest.main()
