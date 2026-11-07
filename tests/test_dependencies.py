import os
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import imageio_ffmpeg
from yt_dlp.downloader.external import FFmpegFD
from yt_dlp.postprocessor.ffmpeg import FFmpegPostProcessor

from videodock.worker import base_options


class BundledDependencyTests(unittest.TestCase):
    def test_partial_download_finds_ffmpeg_without_system_path(self):
        # FFmpegFD.available() does not receive YoutubeDL's ffmpeg_location.
        # Use the versioned imageio binary to also cover a source-only install.
        executable = Path(imageio_ffmpeg.get_ffmpeg_exe())
        token = FFmpegPostProcessor._ffmpeg_location.set(None)
        try:
            with patch.dict(os.environ, {"PATH": ""}), patch("videodock.worker.find_ffmpeg", return_value=executable):
                options = base_options(Mock())
                self.assertEqual(options["ffmpeg_location"], str(executable))
                self.assertTrue(FFmpegFD.available())
        finally:
            FFmpegPostProcessor._ffmpeg_location.reset(token)


if __name__ == "__main__":
    unittest.main()
