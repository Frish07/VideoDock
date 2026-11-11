import tempfile
import unittest
from pathlib import Path

from videodock.core import (DownloadRequest, available_heights, format_selector,
                            format_time, normalize_url, parse_time, parse_video_url, unique_destination,
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
                      "https://youtube.com/watch?v=123", "https://user:pass@youtube.com/watch?v=BaW_jenozKc",
                      "https://www.tiktok.com/@creator", "https://www.tiktok.com/@creator/photo/123",
                      "https://www.instagram.com/reels/audio/123", "https://instagram.com/creator/",
                      "https://facebook.com/share/", "https://facebook.com/flx/warn/?u=https://example.com",
                      "https://instagram.com.example.org/p/Ab123", "https://fb.watch@example.org/Code/"]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_url(value)

    def test_social_video_and_share_links(self):
        cases = [
            ("tiktok.com/@creator/video/123?lang=en", "https://www.tiktok.com/@creator/video/123/", "TikTok"),
            ("https://vm.tiktok.com/Zabc/?foo=bar", "https://vm.tiktok.com/Zabc/", "TikTok"),
            ("https://vt.tiktok.com/Zabc/", "https://vt.tiktok.com/Zabc/", "TikTok"),
            ("https://www.tiktok.com/t/Zabc/", "https://www.tiktok.com/t/Zabc/", "TikTok"),
            ("https://instagram.com/creator/reels/ABC_-/?igsh=123", "https://www.instagram.com/reel/ABC_-/", "Instagram"),
            ("https://instagram.com/p/ABC/", "https://www.instagram.com/p/ABC/", "Instagram"),
            ("https://instagram.com/share/reel/ABC/", "https://www.instagram.com/share/reel/ABC/", "Instagram"),
            ("https://m.facebook.com/watch?v=123", "https://www.facebook.com/watch/?v=123", "Facebook"),
            ("https://www.facebook.com/creator/videos/123/", "https://www.facebook.com/watch/?v=123", "Facebook"),
            ("https://facebook.com/reel/123/?mibextid=abc", "https://www.facebook.com/reel/123/", "Facebook"),
            ("https://facebook.com/share/v/AbC/", "https://www.facebook.com/share/v/AbC/", "Facebook"),
            ("https://fb.watch/aBc/?mibextid=abc", "https://fb.watch/aBc/", "Facebook"),
        ]
        for value, expected, platform in cases:
            with self.subTest(value=value):
                self.assertEqual(parse_video_url(value), (expected, platform))
                self.assertEqual(normalize_url(expected), expected)

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
        self.assertTrue(format_selector(720, "mp4", False, allow_silent=True).endswith("/bestvideo[height<=720]"))

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
