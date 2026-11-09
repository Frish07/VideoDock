from __future__ import annotations

import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory


def ensure_compatible_mp4(source: Path, ffmpeg: Path) -> None:
    """Keep compatible tracks and convert the rest before publishing an MP4."""
    command = [str(ffmpeg), "-hide_banner", "-nostdin"]
    streams = ["-i", str(source), "-map", "0:V:0", "-map", "0:a:0"]
    run_options = {
        "capture_output": True, "encoding": "utf-8", "errors": "replace",
        "creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0),
    }

    # The portable build ships FFmpeg without ffprobe. Read the input stream
    # descriptions before the mapping report, using a zero-duration stream copy.
    probe = subprocess.run([*command, *streams, "-c", "copy", "-t", "0", "-f", "null", "-"], **run_options)
    input_report = probe.stderr.partition("\nStream mapping:")[0]
    videos = re.findall(r"^\s*Stream #0:\d+[^\n]*?: Video: (.+)$", input_report, re.MULTILINE)
    video = next((stream for stream in videos if "(attached pic)" not in stream), "")
    audio = re.search(r"^\s*Stream #0:\d+[^\n]*?: Audio: (.+)$", input_report, re.MULTILINE)
    if probe.returncode or not video or not audio:
        raise RuntimeError(f"Не удалось проверить видео и звук в файле MP4.\n\n{probe.stderr.strip()}")

    copy_video = re.match(r"h264 \((?:Constrained Baseline|Baseline|Main|High)\)[^,]*, yuv420p(?:[,(]|$)",
                          video)
    copy_audio = re.match(r"aac \(LC\)[^,]*, (?:44100|48000) Hz, (?:mono|stereo),", audio[1])
    if copy_video and copy_audio:
        return

    video_options = ["-c:v", "copy"] if copy_video else [
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "high", "-preset", "fast", "-crf", "18",
        "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2",
    ]
    audio_options = ["-c:a", "copy"] if copy_audio else [
        "-c:a", "aac", "-profile:a", "aac_low", "-b:a", "192k", "-ac", "2", "-ar", "48000",
    ]
    with TemporaryDirectory(dir=source.parent, prefix=".compat-") as directory:
        converted = Path(directory) / "compatible.mp4"
        result = subprocess.run(
            [*command, "-loglevel", "error", *streams, *video_options, *audio_options,
             "-movflags", "+faststart", str(converted)],
            **run_options,
        )
        if result.returncode or not converted.is_file() or not converted.stat().st_size:
            raise RuntimeError(f"Не удалось подготовить совместимый MP4.\n\n{result.stderr.strip()}")
        converted.replace(source)
