import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from yt_dlp import YoutubeDL

from videodock.core import DownloadRequest, find_ffmpeg
from videodock.worker import base_options, download


class DownloadOutputTests(unittest.TestCase):
    def test_selects_merged_mp4_when_newer_video_only_file_remains(self):
        root = Path(self.enterContext(tempfile.TemporaryDirectory()))
        video = root / "video.mp4"
        audio = root / "audio.webm"
        output = root / "Выход"
        staging = output / ".videodock-test"
        ffmpeg = find_ffmpeg()
        subprocess.run(
            [str(ffmpeg), "-hide_banner", "-loglevel", "error",
             "-f", "lavfi", "-i", "testsrc2=size=160x90:rate=24:duration=0.5",
             "-f", "lavfi", "-i", "sine=frequency=500:sample_rate=48000:duration=0.5",
             "-map", "0:v", "-c:v", "libx264", str(video),
             "-map", "1:a", "-c:a", "libopus", str(audio)],
            check=True, capture_output=True,
        )
        info = {
            "id": "aqz-KE-bpKQ", "title": "Проверка", "duration": 0.5,
            "extractor": "youtube", "extractor_key": "Youtube",
            "formats": [
                {"url": "https://example.invalid/video.mp4", "format_id": "137", "ext": "mp4",
                 "height": 90, "vcodec": "avc1", "acodec": "none"},
                {"url": "https://example.invalid/audio.webm", "format_id": "251", "ext": "webm",
                 "vcodec": "none", "acodec": "opus"},
            ],
        }
        request = DownloadRequest("https://youtu.be/aqz-KE-bpKQ", str(output))
        events = Mock()
        options = base_options(events)

        def make_intermediate_newer(filepath):
            # A retained source can have a newer timestamp than the merge.
            merged = Path(filepath)
            intermediate = merged.with_suffix(".f137.mp4")
            self.assertTrue(intermediate.is_file())
            earlier = time.time() - 3600
            os.utime(merged, (earlier, earlier))
            os.utime(intermediate, (earlier + 60, earlier + 60))

        def copy_stream(filename, media, **kwargs):
            shutil.copyfile({"137": video, "251": audio}[media["format_id"]], filename)
            return True, True

        options.update(keepvideo=True, post_hooks=[make_intermediate_newer])
        with (patch("videodock.worker.base_options", return_value=options),
              patch.object(YoutubeDL, "extract_info", return_value=info),
              patch.object(YoutubeDL, "dl", side_effect=copy_stream)):
            download(request, events, staging)

        finished = list(output.glob("*.mp4"))
        self.assertEqual([file.name for file in finished], ["Проверка [aqz-KE-bpKQ].mp4"])
        probe = subprocess.run(
            [str(ffmpeg), "-hide_banner", "-nostdin", "-xerror", "-i", str(finished[0]),
             "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-"],
            check=True, capture_output=True, encoding="utf-8", errors="replace",
        ).stderr.partition("Stream mapping:")[0]
        self.assertIn("Video: h264", probe)
        self.assertIn("Audio: aac (LC)", probe)
